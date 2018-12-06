Description
My project is a 2d spaceship fighting game where the spaceships orbit planets. There are many planets which orbit a star. Bullets the player shot also obey gravity and orbit planets. In normal mode, there is a fuel limitation and players might can mine ore from planets. Players can build there ships from different types of parts and save their game by docking at a space station. Normal mode still has some bugs in it and is not quite complete. In simple mode, ships are only one part, there is no fuel limitation, no ore mining, and no space station. Players get upgrades when they destroy other players and can choose to upgrade either engines or bullet speed. In all modes, there is a map in the bottom right corner of the screen and a leaderboard showing the 5 people with the highest scores in the top right. The number of ships you have destroyed is show in the top left.

You can play the game at orbit3.herokuapp.com

How to run
Download the project
Do the following in command prompt / terminal:
install the following (using pip install)
flask
flask-socketio
eventlet
greenlet
itsdangerous
Jinja2
(note: this should be done in command prompt / terminal, not pyzo)
change directory to the project (by using cd)
run the following commands:
set FLASK_APP=flaskr
set FLASK_ENV=development
flask run
If everything worked, the project should be running on localhost:5000

There are no shortcut commands at this time (although clicking on a planet to launch an ore miner to it should be stated more clearly in the directions)