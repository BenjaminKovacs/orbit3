from flask import Flask, render_template
from flask_socketio import SocketIO
from flask_socketio import send, emit

class Circle(object):
    circleList = []
    circleSend = []
    def __init__(this, x,y,r,color):
        this.x = x
        this.y = y
        this.r = r
        this.color = color
        Circle.circleList.append(this)
        Circle.circleSend.append(this.getDict())
        
    def __repr__(this):
        return (this.x,this.y,this.r,this.color)
        
    def getDict(this):
        return {'x':this.x,
                'y':this.y,
                'r':this.r,
                'color':this.color}
                
    @staticmethod
    def getSend():
        Circle.circleSend = []
        for circle in Circle.circleList:
            Circle.circleSend.append(circle.getDict()) 
        return Circle.circleSend
                
# socket.io setup code from https://flask-socketio.readthedocs.io/en/latest/
# flask setup code from http://flask.pocoo.org/docs/1.0/tutorial/
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@app.route('/hello')
def hello():
    return 'Hello, World!'
    
@app.route('/')
def index():
    return render_template('index.html')

c = Circle(10,10,50,'red')
    
@socketio.on('my event')
def handle_message(message):
    print('received message: ' + str(message))
    print('going to send a message now')
    emit('test','sockets work!')
    emit('update', Circle.getSend())

if __name__ == '__main__':
    socketio.run(app)