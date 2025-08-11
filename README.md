
# Project-Siesta
![GitHub Repo stars](https://img.shields.io/github/stars/vinayak-7-0-3/Project-Siesta?style=for-the-badge)
![GitHub forks](https://img.shields.io/github/forks/vinayak-7-0-3/Project-Siesta?style=for-the-badge)
![Docker Pulls](https://img.shields.io/docker/pulls/weebzbots/project-siesta?style=for-the-badge)
[![Static Badge](https://img.shields.io/badge/support-pink?style=for-the-badge)](https://t.me/weebzgroup)

AIO Bot for your music needs on Telegram.

Note: This is not a music streaming / VC Bot

## FEATURES

**Currently the project is in early development stage and features are incomplete**

Feels free to check the repo and report bugs / features

**A complete guide for ~~downloading~~ (coughs..) ehmm.... can be found [here](https://rentry.org/project-siesta)**

## INSTALLATION


#### 1) LOCAL DEPLOYMENT

**Requirements**
- Python>=3.10 (3.12 recommended) 
- Git installed (optional)
- Rclone (optional)
- ffmpeg (optional)

**Steps**
- Git clone (or download) the repo
- Create virtual environment and run
```
virtualenv -p python3 VENV
. ./VENV/bin/activate
```
- Edit and fill out the essentials environment variables in `sample.env` (refer [here](#variables-info))
- Rename `sample.env` to `.env`
- Finally run
```
pip install -r requirements.txt
python -m bot
```

#### 2) USING DOCKER (Manual Build)
**Requirements**
- Git installed (optional)
- Of course Docker installed (how would ya do docker method without docker  🤷‍)

**Steps**
- Git clone (or download) the repo
- Fill out the required variables in `sample.env` (refer [here](#variables-info))
- Build the image using the Docker build command
```
sudo docker build . -t project-siesta
```
- Now run the created Docker image
```
sudo docker run -d --env-file sample.env --name siesta project-siesta
```
- At this point your bot will be running (if everything correct)

#### 3) USING DOCKER (Prebuilt Image)

Premade Docker Images are available at Dockerhub repo `weebzbots/project-siesta`
These images are made using GitHub Actions
- Supported architectures
	- `arm64`
	- `amd64`
- Build Tags
	- `latest` - Latest stable releases from main branch
	- `beta` - Latest beta releases from beta branch (early feature testing)
	- `<commit-hash>` - You can use specific commit hash for specific versions

**Requirements**
- Of course Docker installed (how would ya do docker method without docker  🤷‍)

**Steps**
- Pull the Docker image
```
sudo docker pull weebzcloud/project-siesta
```
- Somewhere in your server, create a `.env` file with required variables (refer [here](#variables-info))
- Run the image
```
sudo docker run -d --env-file .env --name siesta project-siesta
```
- At this point your bot will be running (if everything correct)

## VARIABLES INFO

#### ESSENTIAL VARIABLES
- `TG_BOT_TOKEN` - Telegeam bot token (get it from [BotFather](https://t.me/BotFather))
- `APP_ID` - Your Telegram APP ID (get it from my.telegram.org) `(int)`
- `API_HASH` - Your Telegram APP HASH (get it from my.telegram.org) `(str)`
- `DATABASE_URL` - Postgres database URL (self hosted or any service) `(str)`
- `BOT_USERNAME` - Your Telegram Bot username (with or without `@`) `(str)`
- `ADMINS` - List of Admin users for the Bot (seperated by space) `(str)`

#### OPTIONAL VARIABLES
- `DOWNLOAD_BASE_DIR` - Downloads folder for the bot (folder is inside the working directory of bot) `(str)`
- `LOCAL_STORAGE` - Folder (full path needed) where you want to store the downloaded file the server itself rather than uploading `(str)`
- `RCLONE_CONFIG` - Rclone config as text or URL to file (can ignore this if you add file manually to root of repo) `(str)`
- `RCLONE_DEST` - Rclone destination as `remote-name:folder-in-remote` `(str)`
- `INDEX_LINK` - If index link needed for Rclone uploads (testes with alist) (no trailing slashes `/` ) `(str)`
- `MAX_WORKERS` - Multithreading limit (kind of more speed) `(int)`
- `TRACK_NAME_FORMAT` - Naming format for tracks (check [metadata](https://github.com/vinayak-7-0-3/Project-Siesta/blob/2bbea8572d660a92bb182a360e91791583f4523b/bot/helpers/metadata.py#L16) section for tags supported) `(str)`
- `PLAYLIST_NAME_FORMAT` - Similar to `TRACK_NAME_FORMAT` but for Playlists (Note: all tags might not be available) `(str)`
- `QOBUZ_EMAIL` - Email ID for logging into Qobuz `(str)`
- `QOBUZ_PASSWORD` - Password for logging into Qobuz `(str)`
- `QOBUZ_USER` - User ID for Qobuz (either use Email or this) `(int)`
- `QOBUZ_TOKEN` - User token for Qobuz (either use password or this) `(str)`
- `ENABLE_TIDAL` - To enable the Tidal module - True/False `(bool)`
- `TIDAL_MOBILE` - To enable Tidal Mobile sessions - True/False `(bool)`
- `TIDAL_MOBILE_TOKEN` - HiRes Mobile token for Tidal `(str)`
- `TIDAL_ATMOS_MOBILE_TOKEN` - Atmos Mobile token for Tidal `(str)`
- `TIDAL_TV_TOKEN` - TV/Auto Token for Tidal `(str)`
- `TIDAL_TV_SECRET` - TV/Auto Token for Tidal `(str)`
- `TIDAL_CONVERT_M4A` - Convert the MAX quality tracks to FLAC `(bool)`
- `TIDAL_REFRESH_TOKEN` - Refresh token for login (this overrides every other login)
- `TIDAL_COUNTRY_CODE` - ISO country codes (in uppercase). Only needed when using Refresh Token. 

## CREDITS
- OrpheusDL - https://github.com/yarrm80s/orpheusdl
- Streamrip - https://github.com/nathom/streamrip
- yaronzz - Tidal-Media-Downloader - https://github.com/yaronzz/Tidal-Media-Downloader
- vitiko98 - qobuz-dl - https://github.com/vitiko98/qobuz-dl

## Support Me ❤️
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/I2I7FWQZ4)

TON - `UQBBPkWSnbMWXrM6P-pb96wYxQzLjZ2hhuYfsO-N2pVmznCG`

## Apple Wrapper Controls (Apple Music)

- **Location**: `Settings -> Providers -> Apple Music`
- **Buttons**:
  - `🧩 Setup Wrapper`: Starts an interactive setup that asks for your Apple ID username and password, then runs the wrapper setup script with those credentials. If 2FA is required, the bot will detect it and prompt you to send the 2FA code, then continues automatically.
  - `⏹️ Stop Wrapper`: Stops any running wrapper process. Includes a confirmation step to prevent accidental taps.

### How Setup Works
1. Tap `🧩 Setup Wrapper`.
2. Send your Apple ID username when asked.
3. Send your Apple ID password when asked.
4. The bot runs the setup script with `USERNAME` and `PASSWORD` exported in the environment, equivalent to:
   ```bash
   USERNAME="your_username" PASSWORD="your_password" /usr/src/app/downloader/setup_wrapper.sh
   ```
5. If the wrapper requests 2FA, you will see a prompt. Send the 2FA code as a normal message within 3 minutes.
6. On success, you'll get a confirmation. On failure, the last part of the script output is shown for debugging.

### How Stop Works
- Tap `⏹️ Stop Wrapper` -> Confirm. The bot runs:
  ```bash
  /usr/src/app/downloader/stop_wrapper.sh
  ```
- It kills wrapper processes and frees ports 10020/20020.

### Configuration
- Override script paths with env vars if needed:
  - `APPLE_WRAPPER_SETUP_PATH` (default `/usr/src/app/downloader/setup_wrapper.sh`)
  - `APPLE_WRAPPER_STOP_PATH` (default `/usr/src/app/downloader/stop_wrapper.sh`)

### Notes & Security
- Credentials are only used to start the setup process and are not stored by the bot.
- You can cancel the flow any time by sending `/cancel`.
- If 2FA prompt does not appear (rare), setup continues and completes automatically.