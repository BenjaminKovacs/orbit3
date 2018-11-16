from flask import Flask, render_template
from flask.ext.socketio import SocketIO
from flask.ext.socketio import send, emit

import time
global prevTime
prevTime = time.time()

def getSend(clss):
    result = []
    for item in clss.lst:
        result.append(item.getDict()) 
    return result

class View(object):
    width = 1536
    height = 754
    def __init__(this, x, y):
        this.x = x
        this.y = y
    def getDict(this):
        return {'x':this.x,
                'y':this.y,
                }

class Circle(object):
    lst = []
    circleSend = []
    def __init__(this, x,y,r,color):
        this.x = x
        this.y = y
        this.pos = Point(x,y)
        this.r = r
        this.color = color
        Circle.lst.append(this)
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
        Circle.circleSend = getSend(Circle)
        return Circle.circleSend
        
class Planet(Circle):
    lst = []
    g = 100000;
    def __init__(this,x,y,r,mass,color):
        super().__init__(x,y,r,color)
        this.mass = mass
        Planet.lst.append(this)
        
    def getA(this,pos):
        r = this.pos.subtract(pos)
        return r.direction().scale(Planet.g*this.mass/(r.magnitude()**2))

class Point(object):
    def __init__(this,x,y):
        this.x = x
        this.y = y
    
    def add(this,other):
        return Point(this.x+other.x,this.y+other.y)
        
    def scale(this,n):
        return Point(this.x*n,this.y*n)
        
    def subtract(this,other):
        return this.add(other.scale(-1))
    
    def magnitude(this):
        return (this.x**2+this.y**2)**.5
        
    def direction(this):
        return this.scale(1/this.magnitude())
    
    def getDict(this):
        return {'x':this.x,
                'y':this.y}

class Polygon(object):
    lst = []
    def __init__(this,x,y,points,color):
        this.x = x
        this.y = y
        this.pos = Point(x,y)
        this.points = points
        this.color = color
        Polygon.lst.append(this)
        
    def getDrawPoints(this):
        result = []
        for point in this.points:
            result.append(Point(point.x+this.x,point.y+this.y))
        return result
            
    def getDictPoints(this):
        result = []
        for point in this.getDrawPoints():
            result.append(point.getDict())
        return result
            
    def getDict(this):
        return {'x':this.x,
                'y':this.y,
                'points':this.getDictPoints(),
                'color':this.color}
    
class Ship(object):
    lst = []
    def __init__(this, x, y, mass, vx, vy, color):
        this.x = x
        this.y = y
        this.pos = Point(x,y)
        this.mass = mass
        this.vx = vx
        this.vy = vy
        this.v = Point(vx,vy)
        this.color = color
        this.shapePoints = [Point(-10,0),Point(0,20),Point(10,0)]
        this.shape = Polygon(x,y,this.shapePoints,color)
        Ship.lst.append(this)
        
    def updatePolygon(this):
        this.shape.x = this.pos.x
        this.shape.y = this.pos.y
        print(this.shape.x == this.pos.x)
        
    def moveShip(this,dt):
        for planet in Planet.lst:
            this.v = this.v.add(planet.getA(this.pos).scale(dt))
        this.pos = this.pos.add(this.v.scale(dt))
        this.updatePolygon()
        
    @staticmethod
    def moveAll(dt):
        for ship in Ship.lst:
            print(ship)
            ship.moveShip(dt)
            
                
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

c = Planet(View.width//2,View.height//2,75,100,'red')
global s
s = Ship(View.width//2,View.height//2 - 200, 1,170,0,'blue')
    
@socketio.on('my event')
def handle_message(message):
    global prevTime
    print('received message: ' + str(message))
    print('going to send a message now')
    t = time.time()
    dt = t - prevTime
    maxdt = .02
    dt = min(dt,maxdt)
    if (dt > .01):
        Ship.moveAll(dt)
        prevTime = t
        global s
        print(s.shape.x)
        emit('update', {'circles':Circle.getSend(),
                        'polygons':getSend(Polygon),
                        'rectangles':0})
    # if tab is not open, update not called -> dt very large -> spaceship moves very far from planet
def tick():
    global prevTime
    t = time.time()
    dt = t - prevTime
    Ship.moveAll(dt)
    emit('update', {'circles':Circle.getSend(),
                        'polygons':getSend(Polygon),
                        'rectangles':0})
    prevTime = t
    time.sleep(.02)
    tick()

if __name__ == '__main__':
    socketio.run(app)