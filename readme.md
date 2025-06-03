<h1>HOW TO RUN</h1>

<h3>PREREQUISITES:</h3>

- you need to have Python3 installed. If you are on debian you also need python3-venv.

<h3>SETTING UP THE VIRTUAL ENVIRONMENT:</h3>

- you will also need to recreate the venv folder. you can do this by running (in the project folder):

    <i>[in terminal (linux)]</i>
######
        > source venv/bin/activate

    <i>[in cmd.exe (windows)]</i>
######
        > venv\Scripts\activate.bat

    <i>[in PowerShell (windows)]</i>
######
        > venv\Scripts\activate.ps1

- once you are in the virtual environment, you will then need to run the following command:

######
        > pip install flask flask_sqlalchemy flask_login flask_dance python-dotenv

- once all of the prerequisites are installed, you will need to set up the .env file.

SETTING UP THE .ENV FILE

- first you will need to set up a discord bot, you can do this from the discord developer portal:

  - <https://discord.com/developers/applications/>

- in the oauth2 tab once the bot is created, you will need to add the following url to redirects:

  - <http://localhost:5001/login/discord/authorized>

you will then need to fill in the .env file parameters with the following information:

    FLASK_SECRET_KEY=
        - this should be a randomly generated key, it can be whatever you'd like.

    DISCORD_CLIENT_ID=
        - the client ID of your discord bot.

    DISCORD_CLIENT_SECRET=
        - the client secret for your discord bot.

    OAUTHLIB_INSECURE_TRANSPORT=1
        - leave this at 1 for testing, this allows the discord bot to authorize requests coming from an insecure domain

    MODERATOR_IDS=
        - the discord ID's for any user you want to have moderator permissions. this allows the specified users to remove, restore, and permanently delete posts.

<h3>RUNNING THE SITE</h3>

- once all of the other steps are complete, run the following command in the project folder (and while still in the virtual environment):

######
        > python app.py

- once it's all initialized, go to the following page to test the site:

    <http://localhost:5001/>

<h3>OTHER NOTES</h3>

that should be it! if you have any issues contact me on discord. my username is coo29.
