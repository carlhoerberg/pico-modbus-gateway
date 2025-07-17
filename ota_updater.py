import json
import gc
import os
import requests
import uasyncio as asyncio
import machine
import tarfile
import deflate
import io


class OTAUpdater:
    def __init__(self, github_repo):
        self.github_repo = github_repo
        self.api_url = f"https://api.github.com/repos/{github_repo}"
        self.version_file = "VERSION"
        self.headers = {"User-Agent": "pico-modbus-gateway-ota/1.0 (MicroPython)"}
        self.files_to_exclude = [
            "config.py",
            "Makefile",
            "README.md",
            "LICENSE",
        ]

    def get_current_version(self):
        """Get current version from local VERSION file"""
        try:
            with open(self.version_file, "r") as f:
                return f.read().strip()
        except:
            return "0.0.0"

    async def get_latest_release(self):
        """Get latest release info from GitHub releases API"""
        try:
            # Use GitHub releases API
            releases_url = f"{self.api_url}/releases/latest"
            print(f"[OTA] Fetching latest release: {releases_url}")

            response = requests.get(releases_url, headers=self.headers)
            if response.status_code != 200:
                print(
                    f"[OTA] Failed to fetch latest release: {response.status_code} {response.text}"
                )
                return None

            release_info = response.json()
            response.close()

            release_data = {
                "tag_name": release_info["tag_name"],
                "tarball_url": release_info["tarball_url"],
                "name": release_info["name"],
                "published_at": release_info["published_at"],
            }

            print(
                f"[OTA] Latest release: {release_data['tag_name']} ({release_data['name']})"
            )
            return release_data

        except Exception as e:
            print(f"[OTA] Error fetching latest release: {e}")
            return None

    async def check_for_updates(self):
        """Check GitHub for newer version using releases API"""
        print("[OTA] Checking for updates...")

        try:
            # Get current local version
            current_version = self.get_current_version()
            print(f"[OTA] Current version: {current_version}")

            # Get latest release info
            release_info = await self.get_latest_release()
            if release_info is None:
                print("[OTA] Failed to get latest release")
                return False

            latest_version = release_info["tag_name"]

            # Check if update is needed
            if current_version == latest_version:
                print("[OTA] Already up to date")
                return False

            print(f"[OTA] Update available! {current_version} -> {latest_version}")
            return True, release_info

        except Exception as e:
            print(f"[OTA] Error checking for updates: {e}")
            return False

    async def download_and_extract_release(self, release_info):
        """Download release tar.gz and extract files"""
        try:
            tarball_url = release_info["tarball_url"]
            tag_name = release_info["tag_name"]

            print(f"[OTA] Downloading release tarball from: {tarball_url}")

            # Download and stream decompress the tar.gz file
            response = requests.get(tarball_url, headers=self.headers)
            if response.status_code != 200:
                print(
                    f"[OTA] Failed to download release tarball: {response.status_code}"
                )
                return False

            print(f"[OTA] Downloading and extracting release tarball...")

            # Extract tar.gz file directly from response stream
            try:
                # Create a file-like object from response content
                compressed_stream = io.BytesIO(response.content)
                response.close()

                # Decompress the stream
                with deflate.DeflateIO(
                    compressed_stream, deflate.GZIP
                ) as decompressed_file:
                    # Open as tarfile
                    with tarfile.TarFile(fileobj=decompressed_file) as tar_ref:
                        # Get the root directory name (GitHub creates a folder like "user-repo-commitsha")
                        tar_contents = tar_ref.getnames()
                        if not tar_contents:
                            print("[OTA] Empty tar file")
                            return False

                        # Find the root directory
                        root_dir = tar_contents[0].split("/")[0]

                        # Extract files, filtering out excluded ones
                        extracted_files = []
                        for member in tar_ref.getmembers():
                            # Skip directories and get relative path
                            if member.isdir():
                                continue

                            # Remove the root directory prefix
                            relative_path = "/".join(member.name.split("/")[1:])
                            if not relative_path:
                                continue

                            # Skip excluded files
                            if any(
                                exclude in relative_path
                                for exclude in self.files_to_exclude
                            ):
                                print(f"[OTA] Skipping excluded file: {relative_path}")
                                continue

                            # Skip hidden files and directories
                            if (
                                relative_path.startswith(".")
                                or "/.git" in relative_path
                            ):
                                continue

                            # Extract file
                            try:
                                # Read file data from tar
                                file_data = tar_ref.extractfile(member).read()

                                # Write to destination
                                temp_filename = f"{relative_path}.tmp"
                                with open(temp_filename, "wb") as dest:
                                    dest.write(file_data)

                                # Replace original file
                                os.rename(temp_filename, relative_path)
                                extracted_files.append(relative_path)
                                print(f"[OTA] Extracted: {relative_path}")

                            except Exception as e:
                                print(f"[OTA] Failed to extract {relative_path}: {e}")
                                # Clean up temp file if it exists
                                try:
                                    os.remove(f"{relative_path}.tmp")
                                except:
                                    pass
                                return False

                print(f"[OTA] Successfully extracted {len(extracted_files)} files")
                return extracted_files

            except Exception as e:
                print(f"[OTA] Error extracting tarball: {e}")
                return False

        except Exception as e:
            print(f"[OTA] Error downloading release: {e}")
            return False

    def delete_obsolete_files(self, repo_files):
        """Delete files that exist locally but are no longer in the repository"""
        try:
            # Get list of local files
            local_files = []
            for filename in os.listdir("."):
                if os.path.isfile(filename):
                    # Skip excluded files
                    if not any(
                        exclude in filename for exclude in self.files_to_exclude
                    ):
                        local_files.append(filename)

            # Find files to delete (exist locally but not in repo)
            files_to_delete = []
            for local_file in local_files:
                if local_file not in repo_files:
                    files_to_delete.append(local_file)

            # Delete obsolete files
            deleted_count = 0
            for filename in files_to_delete:
                try:
                    os.remove(filename)
                    print(f"[OTA] Deleted obsolete file: {filename}")
                    deleted_count += 1
                except Exception as e:
                    print(f"[OTA] Failed to delete {filename}: {e}")

            return deleted_count

        except Exception as e:
            print(f"[OTA] Error checking for obsolete files: {e}")
            return 0

    async def perform_update(self):
        """Perform the OTA update"""
        print("[OTA] Starting OTA update...")

        # Check for updates
        update_result = await self.check_for_updates()
        if not update_result:
            return False

        if isinstance(update_result, tuple):
            has_update, release_info = update_result
        else:
            return False

        # Download and extract release zip
        extracted_files = await self.download_and_extract_release(release_info)
        if not extracted_files:
            print("[OTA] Failed to download and extract release")
            return False

        # Delete files that are no longer in the repository
        deleted_count = self.delete_obsolete_files(extracted_files)

        print(
            f"[OTA] Update successful! Updated {len(extracted_files)} files, deleted {deleted_count} files."
        )
        return True

    def restart_device(self):
        """Restart the device"""
        print("[OTA] Restarting device...")
        try:
            machine.reset()
        except:
            print("[INFO] Local test mode - restart not available")

    async def check_and_update(self):
        """Check for updates and perform update if available"""
        try:
            if await self.perform_update():
                print("[OTA] Update completed successfully. Restarting...")
                self.restart_device()
                return True
            else:
                print("[OTA] No update performed")
                return False
        except Exception as e:
            print(f"[OTA] Update failed: {e}")
            return False
