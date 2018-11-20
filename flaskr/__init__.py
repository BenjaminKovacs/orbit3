from flask import Flask, render_template
from flask_socketio import SocketIO
from flask_socketio import send, emit
from flask import request
from flask_socketio import join_room, leave_room

import threading
import eventlet
eventlet.monkey_patch()

import time
import math
import random
global prevTime
prevTime = time.time()

def getSend(clss):
    result = []
    for item in clss.lst:
        result.append(item.getDict()) 
    return result

class User(object):
    userDict = {}
    def __init__(this,id,ship,view):
        this.id = id
        this.ship = ship
        this.view = view
        User.userDict[id] = this
        
    def destroy(this):
        this.ship.destroy()
        this.view.destroy()
        del User.userDict[this.id]

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
    def destroy(this):
        pass

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
        return {'x':this.pos.x,
                'y':this.pos.y,
                'r':this.r,
                'color':this.color}
    #https://brilliant.org/wiki/dot-product-distance-between-point-and-a-line/
    def checkIntersect(this, other):
        if isinstance(other, Circle):
            return this.pos.distance(other.pos) < (this.r+other.r)
        elif isinstance(other, Polygon):
            pts = other.getDrawPoints()
            for i in range(len(pts)):
                vect = pts[i].subtract(pts[i-1])
                n = vect.scale(-1)
                n = Point(n.y,n.x) #perpendicular to side
                n = n.direction()
                l = this.pos.subtract(pts[i])
                d = n.dot(l)
                n = n.scale(abs(d))
                
                if pts[i].distance(this.pos) < this.r:
                    return True
                
                intersect = this.pos.subtract(n)
                xbetween = (pts[i-1].x <= intersect.x <= pts[i].x) or (pts[i].x <= intersect.x <= pts[i-1].x)
                ybetween = (pts[i-1].y <= intersect.y <= pts[i].y) or (pts[i].y <= intersect.y <= pts[i-1].y)
                cross = n.intersectDiff(pts[i].subtract(pts[i-1]))
                if abs(d) <= this.r and cross:
                    return True
                    
            #check if circle is inside polygon
            count = 0
            a = []
            b = []
            c = []
            for i in range(len(pts)):
                ybetween = (pts[i-1].y < this.pos.y < pts[i].y) or (pts[i].y < this.pos.y < pts[i-1].y)
                line = pts[i].subtract(pts[i-1])
                m = line.y/line.x
                if ybetween and ((pts[i-1].x + (this.pos.y-pts[i-1].y)/m) > this.pos.x):
                    a.append((pts[i].x,pts[i].y))
                    b.append((pts[i-1].x,pts[i-1].y))
                    c.append((this.pos.x,this.pos.y))
                    count += 1

            if count%2 == 1:
                #print(count)
                #print(a)
                #print(b)
                #print(c)
                return True
            return False
    
    def destroy(this):
        Circle.lst.remove(this)
        #print('destroyed')
                
    @staticmethod
    def getSend():
        Circle.circleSend = getSend(Circle)
        return Circle.circleSend
        
class Planet(Circle):
    lst = []
    g = 100000;
    def __init__(this,x,y,vx,vy,r,mass,color):
        super().__init__(x,y,r,color)
        this.v = Point(vx,vy)
        this.mass = mass
        Planet.lst.append(this)
    
    def move(this,dt):
        #print(this.pos.x,this.pos.y)
        for planet in Planet.lst:
            #print(planet.x,planet.y)
            if not planet.pos == this.pos:
                this.v = this.v.add(planet.getA(this.pos).scale(dt))
        this.pos = this.pos.add(this.v.scale(dt))
        
    def getA(this, pos):
        r = this.pos.subtract(pos)
        if r.magnitude != 0:
            return r.direction().scale(Planet.g*this.mass/(r.magnitude()**2))
        else:
            return 0
        
    @staticmethod
    def moveAll(dt):
        for planet in Planet.lst:
            planet.move(dt)

class Bullet(Circle):
    lst = []
    def __init__(this,x,y,vx,vy,r,mass,color):
        super().__init__(x,y,r,color)
        this.v = Point(vx,vy)
        this.mass = mass
        this.timeShot = time.time()
        this.life = 10
        Bullet.lst.append(this)
        
    def move(this,dt):
        for planet in Planet.lst:
            this.v = this.v.add(planet.getA(this.pos).scale(dt))
            if this.checkIntersect(planet):
                this.destroy()
        this.pos = this.pos.add(this.v.scale(dt))
    
    def destroy(this):
        super().destroy()
        Bullet.lst.remove(this)
        
    @staticmethod    
    def moveAll(dt):
        for bullet in Bullet.lst:
            bullet.move(dt)
            #print(time.time() - bullet.timeShot)
            if time.time() - bullet.timeShot > bullet.life:
                bullet.destroy()

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
    
    def getAngle(this):
        return math.atan2(this.y,this.x)
        
    def rotate(this,angle):
        angle = this.getAngle() - angle
        pt = getDir(angle).scale(this.magnitude())
        this.x = pt.x
        this.y = pt.y
    
    def dot(this,other):
        return this.x*other.x + this.y*other.y
        
    def intersectDiff(this,other):
        return intersect(Point(0,0),this,Point(0,0),other)
    
    def distance(this,other):
        return ((this.x-other.x)**2 + (this.y-other.y)**2)**.5
    
    def getDict(this):
        return {'x':this.x,
                'y':this.y}
                
    def __eq__(this,other):
        return this.x == other.x and this.y == other.y
                
# https://stackoverflow.com/questions/3838329/how-can-i-check-if-two-segments-intersect
def ccw(A,B,C):
    return (C.y-A.y) * (B.x-A.x) > (B.y-A.y) * (C.x-A.x)

# Return true if line segments AB and CD intersect
def intersect(A,B,C,D):
    return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)

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
        return {'x':this.pos.x,
                'y':this.pos.y,
                'points':this.getDictPoints(),
                'color':this.color}
    
    def rotate(this,angle):
        for point in this.points:
            point.rotate(angle)
                
    def destroy(this):
        Polygon.lst.remove(this)

def getDir(angle):
    return Point(math.cos(angle),math.sin(angle))

class Engine(object):
    def __init__(this,force):
        this.force = force
    def destroy(this):
        pass

class Weapon(object):
    def __init__(this, bmass, bspeed, bcolor, br):
        this.bmass = bmass
        this.bspeed = bspeed
        this.bcolor = bcolor
        this.br = br
        
    def shoot(this, x,y, svx,svy, direction):
        v = direction.scale(this.bspeed)
        Bullet(x,y, v.x+svx,v.y+svy,this.br,this.bmass,this.bcolor)
    
class Ship(object):
    lst = []
    def __init__(this, x, y, mass, vx, vy, color, id):
        this.x = x
        this.y = y
        this.pos = Point(x,y)
        this.mass = mass
        this.vx = vx
        this.vy = vy
        this.v = Point(vx,vy)
        this.color = color
        this.shapePoints = [Point(-10,0),Point(0,30),Point(10,0)]
        this.shape = Polygon(x,y,this.shapePoints,color)
        
        this.id = id
        this.angle = math.pi / 2
        this.turn = 0
        this.throttle = 0
        this.engine = Engine(1)
        this.weapon = Weapon(1, 200, 'orange', 2)
        
        Ship.lst.append(this)
        
    def updatePolygon(this):
        this.shape.x = this.pos.x
        this.shape.y = this.pos.y
        #print('pos',this.pos.x,this.pos.y)
        
    def moveShip(this,dt):
        #print(this.pos.x,this.pos.y)
        this.angle -= this.turn
        this.shape.rotate(this.turn)
        this.v = this.v.add(getDir(this.angle).scale(this.throttle*this.engine.force/this.mass).scale(dt))
        for planet in Planet.lst:
            this.v = this.v.add(planet.getA(this.pos).scale(dt))
        this.pos = this.pos.add(this.v.scale(dt))
        this.updatePolygon()
        for bullet in Bullet.lst:
            if ((time.time() - bullet.timeShot) > .1) and bullet.checkIntersect(this.shape):
                this.destroy()
                bullet.destroy()
                break
        for planet in Planet.lst:
            if planet.checkIntersect(this.shape):
                #print('yay')
                this.destroy()
                break
        maxDist = 1 * View.width
        planetVector = Planet.lst[0].pos.subtract(this.pos)
        if planetVector.magnitude() > maxDist:
            this.v = planetVector.scale(.1)
    
    def shoot(this):
        x = this.pos.x + this.shape.points[1].x
        y = this.pos.y + this.shape.points[1].y
        this.weapon.shoot(x,y,this.v.x,this.v.y,getDir(this.angle))
        
    def destroy(this):
        #print(len(Ship.lst))
        this.shape.destroy()
        this.engine.destroy()
        Ship.lst.remove(this)
        socketio.emit('destroyed','stuff',room=this.id)
        
    @staticmethod
    def moveAll(dt):
        for ship in Ship.lst:
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

c = Planet(View.width//2,View.height//2, 0, 0, 75,100,'red')
#c = Planet(View.width//2,View.height//2-400, -100, 0, 75,100,'red')
for i in range(10):
    for j in range(10):
        Circle(i*View.width/10,j*View.height/10, 10, 'yellow')
global s
#s = Ship(View.width//2,View.height//2 - 200, 1,170,0,'blue')
#Ship(View.width//2,View.height//2 + 200, 1, 170,0,'green')   
global room 
@socketio.on('my event')
def handle_message(message):
    global room
    room = 'main'
    global prevTime
    #print('received message: ' + str(message))
    print('going to send a message now')
    t = time.time()
    dt = t - prevTime
    maxdt = .02
    dt = min(dt,maxdt)
    join_room('main')
    if (dt > .01):
        Ship.moveAll(dt)
        prevTime = t
        emit('update', {'circles':Circle.getSend(),
                        'polygons':getSend(Polygon),
                        'rectangles':0})
    # if tab is not open, update not called -> dt very large -> spaceship moves very far from planet
    
@socketio.on('first start')
def start():
    print('a user connected')
    color = random.choice(['blue','green','white','yellow'])
    s = Ship(View.width//2,View.height//2 + 400, 1,170,0,color,request.sid)
    User(request.sid, s, View(s.x,s.y))
    join_room('main')

@socketio.on('start again')
def restart():
    color = random.choice(['blue','green','white','yellow'])
    s = Ship(View.width//2,View.height//2 + 400, 1,170,0,color,request.sid)
    User.userDict[request.sid].ship = s;
 
@socketio.on('fire engine')
def updateMotion(value):
    value = min(value,1)
    User.userDict[request.sid].ship.throttle = value*100
    #print('accelerating')
    
@socketio.on('rotate')
def rotate(value):
    value = max(min(value,1),-1)
    User.userDict[request.sid].ship.turn = value*.1
    #print('turning')

@socketio.on('shoot')
def fire():
    User.userDict[request.sid].ship.shoot()
    
def tick():
    while True:
        global room
        global prevTime
        t = time.time()
        dt = t - prevTime
        Ship.moveAll(dt)
        Bullet.moveAll(dt)
        Planet.moveAll(dt)
        socketio.emit('update', {'circles':Circle.getSend(),
                            'polygons':getSend(Polygon),
                            'rectangles':0}, namespace='/', broadcast=True)
        prevTime = t
        for user in User.userDict.keys():
            socketio.emit('view',User.userDict[user].ship.pos.getDict(),room=User.userDict[user].id)
        eventlet.sleep(.01)

#thread = threading.Thread(target=tick)
#thread.start()
eventlet.spawn(tick)

if __name__ == '__main__':
    socketio.run(app)