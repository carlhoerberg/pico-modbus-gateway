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
        self.commit_file = "current_commit.txt"
        self.headers = {
            "User-Agent": "pico-modbus-gateway/1.0"
        }
        self.files_to_exclude = [
            self.commit_file,
            "config.py",
            "Makefile",
            "README.md",
            "LICENSE",
        ]

    def get_current_commit(self):
        """Get current commit hash from file"""
        try:
            with open(self.commit_file, "r") as f:
                return f.read().strip()
        except:
            return ""

    def save_commit(self, commit_sha):
        """Save current commit hash to file"""
        try:
            with open(self.commit_file, "w") as f:
                f.write(commit_sha)
        except Exception as e:
            print(f"Failed to save commit: {e}")

    async def get_repo_files(self, commit_sha):
        """Get list of files from repository"""
        try:
            # Get repository contents
            contents_url = f"{self.api_url}/contents?ref={commit_sha}"
            print(f"[OTA] Fetching repository contents: {contents_url}")

            response = requests.get(contents_url, headers=self.headers)
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

    async def check_for_updates(self):
        """Check GitHub for newer commits"""
        print("[OTA] Checking for updates...")

        try:
            # Get current commit hash
            current_commit = self.get_current_commit()
            print(
                f"[OTA] Current commit: {current_commit[:8] if current_commit else 'none'}"
            )

            # Get latest commit from GitHub
            commits_url = f"{self.api_url}/commits/main"
            print(f"[OTA] Fetching: {commits_url}")

            response = requests.get(commits_url, headers=self.headers)
            if response.status_code != 200:
                print(f"[OTA] Failed to fetch commits: {response.status_code}")
                return False

            commits = response.json()
            response.close()

            latest_commit = commits["sha"]
            print(f"[OTA] Latest commit: {latest_commit[:8]}")

            # Check if update is needed
            if current_commit == latest_commit:
                print("[OTA] Already up to date")
                return False

            print("[OTA] Update available!")
            return True, latest_commit

        except Exception as e:
            print(f"[OTA] Error checking for updates: {e}")
            return False

    async def download_file(self, filename, commit_sha):
        """Download a single file from GitHub"""
        try:
            # GitHub raw content URL
            file_url = f"https://raw.githubusercontent.com/{self.github_repo}/{commit_sha}/{filename}"
            print(f"[OTA] Downloading {filename}...")

            response = requests.get(file_url, headers=self.headers)
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
                try:
                    # Check if it's a file using os.stat
                    stat_info = os.stat(filename)
                    # Check if it's a regular file (not directory)
                    if stat_info[0] & 0x8000:  # S_IFREG
                        # Skip excluded files
                        if not any(
                            exclude in filename for exclude in self.files_to_exclude
                        ):
                            local_files.append(filename)
                except:
                    # Skip if we can't stat the file
                    pass

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
            has_update, latest_commit = update_result
        else:
            return False

        # Get list of files from repository
        files_to_update = await self.get_repo_files(latest_commit)
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

            if await self.download_file(filename, latest_commit):
                success_count += 1
            else:
                failed_files.append(filename)

        # Check if update was successful
        if success_count == len(files_to_update):
            print(
                f"[OTA] Update successful! Updated {success_count} files, deleted {deleted_count} files."
            )
            # Save new commit hash
            self.save_commit(latest_commit)
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
