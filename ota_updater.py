import json
import gc
import os
import requests
import uasyncio as asyncio
import machine


class OTAUpdater:
    def __init__(self, github_repo):
        self.github_repo = github_repo
        self.api_url = f"https://api.github.com/repos/{github_repo}"
        self.version_file = "VERSION"
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

    async def get_repo_files(self, tag_name):
        """Get list of files from repository at specific tag"""
        try:
            # Get repository contents at tag
            contents_url = f"{self.api_url}/contents?ref={tag_name}"
            print(f"[OTA] Fetching repository contents for tag {tag_name}: {contents_url}")

            response = requests.get(contents_url)
            if response.status_code != 200:
                print(f"[OTA] Failed to fetch contents: {response.status_code}")
                return []

            contents = response.json()
            response.close()

            files = []
            for item in contents:
                if item["type"] == "file":
                    filename = item["name"]
                    # Skip excluded files
                    if not any(
                        exclude in filename for exclude in self.files_to_exclude
                    ):
                        files.append(filename)
                        print(f"[OTA] Found file: {filename}")

            return files

        except Exception as e:
            print(f"[OTA] Error fetching repository files: {e}")
            return []

    async def get_remote_version(self):
        """Get remote version from GitHub using direct raw access"""
        try:
            # Use raw GitHub content URL to get VERSION file
            version_url = f"https://raw.githubusercontent.com/{self.github_repo}/main/VERSION"
            print(f"[OTA] Fetching remote version: {version_url}")

            response = requests.get(version_url)
            if response.status_code != 200:
                print(f"[OTA] Failed to fetch VERSION file: {response.status_code}")
                return None

            remote_version = response.text.strip()
            response.close()
            print(f"[OTA] Remote version: {remote_version}")
            return remote_version

        except Exception as e:
            print(f"[OTA] Error fetching remote version: {e}")
            return None

    async def check_for_updates(self):
        """Check GitHub for newer version using VERSION file"""
        print("[OTA] Checking for updates...")

        try:
            # Get current local version
            current_version = self.get_current_version()
            print(f"[OTA] Current version: {current_version}")

            # Get remote version
            remote_version = await self.get_remote_version()
            if remote_version is None:
                print("[OTA] Failed to get remote version")
                return False

            # Check if update is needed
            if current_version == remote_version:
                print("[OTA] Already up to date")
                return False

            print(f"[OTA] Update available! {current_version} -> {remote_version}")
            return True, remote_version

        except Exception as e:
            print(f"[OTA] Error checking for updates: {e}")
            return False

    async def download_file(self, filename, tag_name):
        """Download a single file from GitHub at specific tag"""
        try:
            # GitHub raw content URL for specific tag
            file_url = f"https://raw.githubusercontent.com/{self.github_repo}/{tag_name}/{filename}"
            print(f"[OTA] Downloading {filename} from tag {tag_name}...")

            response = requests.get(file_url)
            if response.status_code != 200:
                print(f"[OTA] Failed to download {filename}: {response.status_code}")
                return False

            # Save to temporary file first
            temp_filename = f"{filename}.tmp"
            with open(temp_filename, "w") as f:
                f.write(response.text)
            response.close()

            # Replace original file
            try:
                os.rename(temp_filename, filename)
                print(f"[OTA] Updated {filename}")
                return True
            except Exception as e:
                print(f"[OTA] Failed to replace {filename}: {e}")
                try:
                    os.remove(temp_filename)
                except:
                    pass
                return False

        except Exception as e:
            print(f"[OTA] Error downloading {filename}: {e}")
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
            has_update, new_version = update_result
        else:
            return False

        # Get list of files from repository at the new version tag
        files_to_update = await self.get_repo_files(new_version)
        if not files_to_update:
            print("[OTA] No files found to update")
            return False

        # Delete files that are no longer in the repository
        deleted_count = self.delete_obsolete_files(files_to_update)

        # Download all files
        success_count = 0
        failed_files = []

        for filename in files_to_update:
            gc.collect()  # Free memory
            await asyncio.sleep(0.1)  # Yield control

            if await self.download_file(filename, new_version):
                success_count += 1
            else:
                failed_files.append(filename)

        # Check if update was successful
        if success_count == len(files_to_update):
            print(
                f"[OTA] Update successful! Updated {success_count} files, deleted {deleted_count} files."
            )
            return True
        else:
            print(
                f"[OTA] Update partially failed. Updated {success_count}/{len(files_to_update)} files, deleted {deleted_count} files."
            )
            print(f"[OTA] Failed files: {failed_files}")
            return False

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
