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
import copy

# socket.io setup code from https://flask-socketio.readthedocs.io/en/latest/
# flask setup code from http://flask.pocoo.org/docs/1.0/tutorial/
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

global prevTime   
prevTime = {}

def createGame(name, upgradeType='simple', fuelLimit=False, oreMining=False):
    global prevTime
    prevTime[name] = time.time()
    
    def getSend(clss):
        result = []
        for item in clss.lst:
            d = item.getDict()
            if d != None:
                result.append(d) 
        return result
    
    class User(object):
        scoreboard = []
        userDict = {}
        def __init__(this,id,ship,view, name):
            this.id = id
            this.ship = ship
            this.view = view
            this.name = name
            this.score = 0
            User.userDict[id] = this
            if upgradeType == 'ship builder':
                this.shipSet = False
                this.builtShip = None
            
        def destroy(this):
            this.ship.destroy()
            this.view.destroy()
            del User.userDict[this.id]
            
    def updateScoreboard():
        #https://stackoverflow.com/questions/403421/how-to-sort-a-list-of-objects-based-on-an-attribute-of-the-objects
        #https://www.pythoncentral.io/convert-dictionary-values-list-python/
        scores = list(User.userDict.values())
        scores.sort(key=lambda x: x.score)
        highScores = scores[:-6:-1]
        sendScores = []
        for s in highScores:
            sendScores.append(s.name+': '+str(s.score)) 
        socketio.emit('high scores', sendScores, namespace='/'+name)
        
    
    def getMini(shape):
        mini = shape.pos.subtract(View.center)
        if mini.magnitude() != 0:
            mini = mini.direction().scale(1/5 * mini.magnitude())
            #(100*math.log(mini.magnitude()))
            #(1/100 * mini.magnitude()*math.log(mini.magnitude())**2)
        mini = mini.add(View.center)
        #mini = mini.getDict()
        return mini
    
    class Text(object):
        lst = []
        def __init__(this,x,y,txt,color='white',font='12px Arial'):
            this.x = x
            this.y = y
            this.text = txt
            this.color = color
            this.font = font
            Text.lst.append(this)
            
        def getDict(this):
            return {'x':this.x,
                    'y':this.y,
                    'text':this.text,
                    'color':this.color,
                    'font':this.font}
                    
        def destroy(this):
            Text.lst.remove(this)
            
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
            mini = getMini(this)
            mini = mini.getDict()
            return {'x':this.pos.x,
                    'y':this.pos.y,
                    'r':this.r,
                    'color':this.color,
                    'mini':mini}
        #https://brilliant.org/wiki/dot-product-distance-between-point-and-a-line/
        #https://gamedev.stackexchange.com/questions/7735/how-do-i-test-if-a-circle-and-concave-polygon-intersect
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
                # TODO: change to using ptInPolygon function if it works
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
                    return True
                return False
        
        def destroy(this):
            try:
                Circle.lst.remove(this)
            except:
                print('WARNING: Circle does not exist')
        
        def pointIn(this, pt):
            return pt.subtract(this.pos).magnitude() <= this.r
                    
        @staticmethod
        def getSend():
            Circle.circleSend = getSend(Circle)
            return Circle.circleSend
    
    class Rectangle(object):
        lst = []
        def __init__(this,x,y,width,height,color):
            this.x = x
            this.y = y
            this.pos = Point(x,y)
            this.width = width
            this.height = height
            this.color = color
            Rectangle.lst.append(this)
            
        def getDict(this):
            return {'x':this.pos.x,
                    'y':this.pos.y,
                    'width':this.width,
                    'height':this.height,
                    'color':this.color
                    }
                    
        def destroy(this):
            try:
                Rectangle.lst.remove(this)
            except:
                print('WARNING: Rectangle does not exist')
            
    class Planet(Circle):
        lst = []
        g = 20;
        def __init__(this,x,y,vx,vy,r,mass,color,bodyOfInfluence,frozen=False):
            super().__init__(x,y,r,color)
            this.v = Point(vx,vy)
            this.bodyOfInfluence = bodyOfInfluence
            this.mass = mass
            this.frozen = frozen
            Planet.lst.append(this)
        
        def move(this,dt):
            #print(this.pos.x,this.pos.y)
            if not this.frozen:
                this.v = this.v.add(this.bodyOfInfluence.getA(this.pos).scale(dt))
            this.pos = this.pos.add(this.v.scale(dt))
            
        def getA(this, pos):
            r = this.pos.subtract(pos)
            if r.magnitude() != 0:
                return r.direction().scale(Planet.g*this.mass/(r.magnitude()**2))
            else:
                return 0
            
        @staticmethod
        def moveAll(dt):
            for planet in Planet.lst:
                planet.move(dt)
    
    class Bullet(Circle):
        lst = []
        def __init__(this,x,y,vx,vy,r,mass,color,id):
            super().__init__(x,y,r,color)
            this.v = Point(vx,vy)
            this.mass = mass
            this.timeShot = time.time()
            this.life = 10
            this.id = id
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
            
        def addA(this,other):
            this.x += other.x
            this.y += other.y
            return this
            
        def scale(this,n):
            return Point(this.x*n,this.y*n)
            
        def subtract(this,other):
            return this.add(other.scale(-1))
            
        def subtractA(this,other):
            return this.addA(other.scale(-1))
        
        def magnitude(this):
            return (this.x**2+this.y**2)**.5
            
        def direction(this):
            if this.magnitude() == 0:
                return Point(0,0)
            return this.scale(1/this.magnitude())
        
        def getAngle(this):
            return math.atan2(this.y,this.x)
            
        def rotate(this,angle):
            angle = this.getAngle() - angle
            pt = getDir(angle).scale(this.magnitude())
            this.x = pt.x
            this.y = pt.y
        
        def setAngle(this,angle):
            angle *= -1
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
    
    def getDictPointsMini(points):
        result = []
        for point in points:
            result.append(point.getDict())
        return result
    
    class Polygon(object):
        lst = []
        def __init__(this,x,y,points,color, hide=False):
            this.x = x
            this.y = y
            this.pos = Point(x,y)
            this.points = points
            this.color = color
            this.hide=hide
            Polygon.lst.append(this)
        
        def updatePos(this):
            this.pos.x = this.x
            this.pos.y = this.y
        
        def getDrawPointsC(this,pt):
            result = []
            for point in this.points:
                result.append(Point(point.x+pt.x,point.y+pt.y))
            return result
            
        def getDrawPoints(this):
            return this.getDrawPointsC(this)
        
                
        def getDictPoints(this):
            result = []
            for point in this.getDrawPoints():
                result.append(point.getDict())
            return result
                
        def getDict(this):
            if this.hide:
                return None
            this.pos.x = this.x
            this.pos.y = this.y
            mini = getMini(this)
            mini.points = this.getDrawPointsC(mini)
            mini.points = getDictPointsMini(mini.points)
            return {'x':this.pos.x,
                    'y':this.pos.y,
                    'points':this.getDictPoints(),
                    'color':this.color,
                    'mini':mini.points}
        
        def rotate(this,angle, pt=Point(0,0)):
            for point in this.points:
                #print(point.x,point.y,pt.x,pt.y)
                point.subtractA(pt).rotate(angle)
                point.addA(pt)
        
        def setAngle(this,angle):
            for point in this.points:
                point.setAngle(angle)
                    
        def destroy(this):
            try:
                Polygon.lst.remove(this)
            except:
                print('WARNING: Polygon does not exist')
            
        def ptInPolygon(this,point):
            this.pos.x = this.x
            this.pos.y = this.y
            count = 0
            pts = this.points
            adjPt = point.subtract(this.pos)
            for i in range(len(pts)):
                ybetween = (pts[i-1].y < adjPt.y < pts[i].y) or (pts[i].y < adjPt.y < pts[i-1].y)
                line = pts[i].subtract(pts[i-1])
                m = line.y/line.x
                if ybetween and ((pts[i-1].x + (adjPt.y-pts[i-1].y)/m) > adjPt.x):
                    count += 1
            if count%2 == 1:
                return True
    
    def getDir(angle):
        return Point(math.cos(angle),math.sin(angle))
    
    class Engine(object):
        def __init__(this,force,x,y):
            this.force = force
            this.exhaustPoints = [Point(-8,0),Point(0,-10),Point(8,0)]
            this.exhaust = Polygon(x,y,this.exhaustPoints,'orange',True)
        
        def fire(this,ship,dt):
            if not (fuelLimit and ship.fuel <= 0):
                ship.v = ship.v.add(getDir(ship.angle).scale(ship.throttle*this.force/ship.mass).scale(dt))
                #this.exhaust.x = this.shape.x
                #this.exhaust.y = this.shape.y
                this.exhaust.hide = (ship.throttle == 0)
                if fuelLimit:
                    fuelUsed = ship.throttle*.001
                    ship.fuel -= fuelUsed
                    ship.mass -= fuelUsed * ship.fuelMass
                    ship.updateFuel()
            else:
                this.exhaust.hide = True
                print('out of fuel')
        
        def rotate(this,angle,pt):
            this.exhaust.rotate(angle,pt)
        
        def move(this):
            this.exhaust.x = this.shape.x
            this.exhaust.y = this.shape.y
            
        def destroy(this):
            this.exhaust.destroy()
    
    class Basic(Engine):
        def __init__(this, x, y):
            force = 1
            super().__init__(force,x,y)
            this.efficiency = 1
            this.points = [Point(-8,-4),Point(-5,0),Point(5,0),Point(8,-4)]
            this.color = 'green'
            this.shape = Polygon(x,y,this.points,this.color)
            this.mass = 1.2
            this.cost = 3
            
        def destroy(this):
            super().destroy()
            this.shape.destroy()
            
        def update(this,x,y):
            this.shape.x = x
            this.shape.y = y
            
        def __repr__(this):
            return 'Basic('+str(this.shape.x)+','+str(this.shape.y)+')'
    
    class Weapon(object):
        def __init__(this, bmass, bspeed, bcolor, br, id):
            this.bmass = bmass
            this.bspeed = bspeed
            this.bcolor = bcolor
            this.br = br
            this.id = id
            
        def shoot(this, x,y, svx,svy, direction):
            v = direction.scale(this.bspeed)
            Bullet(x,y, v.x+svx,v.y+svy,this.br,this.bmass,this.bcolor, this.id)
    
    class View(object):
        width = 1536
        height = 754
        maxDist = 2 * width
        center = Point(width/2,height/2)
        def __init__(this, x, y):
            this.x = x
            this.y = y
        def getDict(this):
            return {'x':this.x,
                    'y':this.y,
                    }
        def destroy(this):
            pass
            
    class ControlUnit(object):
        def __init__(this,x,y):
            this.x = x
            this.y = y
            this.pos = Point(x,y)
            this.mass = .4
            this.cost = 0
            this.color = 'blue'
            this.shapePoints = [Point(-10,0),Point(0,30),Point(10,0)]
            this.shape = Polygon(x,y,this.shapePoints,this.color)
            
        def __repr__(this):
            return 'ControlUnit('+str(this.shape.x)+','+str(this.shape.y)+')' 
            
        def update(this,x,y):
            this.shape.x = x
            this.shape.y = y
            
        def destroy(this):
            this.shape.destroy()
    
    class FuelTank(object):
        def __init__(this,x,y):
            this.x = x
            this.y = y
            this.pos = Point(x,y)
            this.mass = .2
            this.fuel = 100
            this.cost = 1
            this.color = 'yellow'
            #TODO: make it so that polygons can have vertical lines
            this.shapePoints = [Point(-10.00001,-20),Point(10,-20),Point(10.00001,0),Point(-10,0.000001)]
            this.shape = Polygon(x,y,this.shapePoints,this.color)
            
        def __repr__(this):
            return 'FuelTank('+str(this.shape.x)+','+str(this.shape.y)+')' 
            
        def update(this,x,y):
            this.shape.x = x
            this.shape.y = y
            
        def destroy(this):
            this.shape.destroy()
    
    #TODO: make ore miners obey the laws of physics        
    class OreMiner(object):
        lst = []
        def __init__(this,x,y, target):
            this.x = x
            this.y = y
            this.speed = 300
            this.pos = Point(x,y)
            this.target = target
            this.mass = 1
            this.ore = 0
            this.capacity = 100
            this.color = 'pink'
            this.landed = False
            this.shapePoints = [Point(-10.00001,-20),Point(10,-20),Point(10.00001,0),Point(-10,0.000001)]
            this.shape = Polygon(x,y,this.shapePoints,this.color)
            OreMiner.lst.append(this)
        
        def updatePolygon(this):
            this.shape.x = this.pos.x
            this.shape.y = this.pos.y
            
        def move(this,dt):
            if not this.target.checkIntersect(this.shape) and not this.landed:
                this.pos = this.pos.add(this.pos.subtract(this.target.pos).direction().scale(this.speed*dt*-1))
            else:
                if not this.landed:
                    this.posRel = this.pos.subtract(this.target.pos)
                    this.landed = True
                    print(this.posRel.x,this.posRel.y)
                print('this',this.pos.x,this.pos.y)
                this.ore += dt
                this.pos = this.posRel.add(this.target.pos)
                print('target',this.target.pos.x,this.target.pos.y)
                print('updated',this.pos.x,this.pos.y)
            this.updatePolygon()
                
        def destroy(this):
            this.shape.destroy()
            
        @staticmethod
        def moveAll(dt):
            for miner in OreMiner.lst:
                miner.move(dt)
              
    class Ship(object):
        lst = []
        def __init__(this, x, y, mass, vx, vy, color, id, name, parts=[]):
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
            
            this.health = 100
            this.maxHealth = this.health
            this.lifeBarSize = 20
            this.lifeBar = Rectangle(x,y-10,this.lifeBarSize,5,'green')
            
            if (upgradeType == 'simple'):
                this.upgrades = 0
                this.engine = Engine(1, x, y)
                this.weapon = Weapon(2, 100, 'orange', 2, id) #old bspeed = 200 bmass = 1
                this.fuel = 100
            
            elif (upgradeType == 'ship builder'):
                this.engine = Basic(x,y)
                this.weapon = Weapon(2, 100, 'orange', 2, id) #old bspeed = 200 bmass = 1
                #exec(parts)#exec(parts)
                #ControlUnit(0,0)
                #https://docs.python.org/3/library/functions.html#exec
                #https://docs.python.org/3/reference/executionmodel.html#naming-and-binding
                print('===============================================')
                print(len(Polygon.lst))
                this.partDict = eval(parts[5:],{'ControlUnit':ControlUnit,'Basic':Basic,'FuelTank':FuelTank})#ship
                print(len(Polygon.lst))
                print('===============================================')
                x = this.partDict['Control'][0].shape.x
                y = this.partDict['Control'][0].shape.y
                this.relativeParts = []
                this.parts = []
                this.mass = .00001
                this.cost = 0
                this.money = 5
                tooExpensive = False
                print(tooExpensive)
                for k in this.partDict.keys():
                    for part in this.partDict[k]:
                        print(tooExpensive)
                        this.parts.append(part)
                        this.relativeParts.append(Point(part.shape.x - x,part.shape.y - y))
                        this.mass += part.mass
                        this.cost += part.cost
                        if this.cost > this.money:
                            this.parts.pop()
                            this.relativeParts.pop()
                            this.mass -= part.mass
                            this.cost -= part.cost
                            part.destroy()
                            tooExpensive = True
                print(tooExpensive)            
                if tooExpensive:
                    socketio.emit('too expensive', room=id,namespace='/'+name)
                
                this.fuel = 0 
                this.fuelMass = .05 
                print(this.partDict)      
                for tank in this.partDict['Fuel tanks']:
                    this.fuel += tank.fuel
                this.mass += this.fuel * this.fuelMass
                    
            #TODO: create class for stats bars instead of handling them individually
            if fuelLimit:
                this.maxFuel = this.fuel
                this.fuelBarSize = 20
                this.fuelBar = Rectangle(x,y-15,this.fuelBarSize,5,'red')
                
            
            this.id = id
            this.angle = math.pi / 2
            this.turn = 0
            this.throttle = 0
            
            
            this.name = name
            this.nameDisplay = Text(x,y,name)
            
            Ship.lst.append(this)
            
        def updatePolygon(this):
            this.shape.x = this.pos.x
            this.shape.y = this.pos.y
            this.nameDisplay.x = this.pos.x
            this.nameDisplay.y = this.pos.y + 15
            if upgradeType != 'ship builder':
                this.engine.exhaust.x = this.pos.x
                this.engine.exhaust.y = this.pos.y
            try:
                this.lifeBar.pos.x = this.pos.x
                this.lifeBar.pos.y = this.pos.y - 10
            except:
                #print("this ship doesn't have a life bar")
                pass
            if fuelLimit:
                try:
                    this.fuelBar.pos.x = this.pos.x
                    this.fuelBar.pos.y = this.pos.y - 15
                except:
                    pass
            if upgradeType == 'ship builder' and this.parts != None:
                this.moveParts(this.pos.x,this.pos.y)
        
        def moveParts(this,x,y):
            for i in range(len(this.parts)):
                part = this.parts[i]
                rpart = this.relativeParts[i]
                part.shape.x = x + rpart.x
                part.shape.y = y + rpart.y
                #try:
                if isinstance(part,Engine):
                    part.move()
                    #print('it moves',type(part))
               # except:
               #     print('it breaks',type(part),e)
                 #   pass
                #print('x',rpart.x,'y',rpart.y)
                
            
        def moveShip(this,dt):
            this.angle -= this.turn
            this.shape.rotate(this.turn)
            
            if upgradeType == 'ship builder' and this.parts != None:
                for part in this.parts:
                    #part.shape.updatePos()
                    part.shape.rotate(this.turn, this.pos.subtract(part.shape.pos)) #why does pos not need to be updated?
                    try:
                        part.rotate(this.turn, this.pos.subtract(part.shape.pos))
                    except:
                        pass
                for engine in this.partDict['Engines']:
                    engine.fire(this,dt)
            else:
                this.engine.exhaust.rotate(this.turn)
                this.v = this.v.add(getDir(this.angle).scale(this.throttle*this.engine.force/this.mass).scale(dt))
                this.engine.exhaust.hide = (this.throttle == 0)
                
            for planet in Planet.lst:
                this.v = this.v.add(planet.getA(this.pos).scale(dt))
            this.pos = this.pos.add(this.v.scale(dt))
            this.updatePolygon()
            if upgradeType != 'ship builder':
                for bullet in Bullet.lst:
                    if ((time.time() - bullet.timeShot) > .1) and bullet.checkIntersect(this.shape):
                        this.hit(bullet)
                        #this.destroy()
                        bullet.destroy()
                        break
                for planet in Planet.lst:
                    if planet.checkIntersect(this.shape):
                        this.destroy()
                        break
            else:
                for part in this.parts:
                    for bullet in Bullet.lst:
                        if ((time.time() - bullet.timeShot) > .1) and bullet.checkIntersect(part.shape):
                            this.hit(bullet)
                            #this.destroy()
                            bullet.destroy()
                            break
                    for planet in Planet.lst:
                        if planet.checkIntersect(part.shape):
                            this.destroy()
                            break
            planetVector = Planet.lst[0].pos.subtract(this.pos)
            if planetVector.magnitude() > View.maxDist:
                this.v = planetVector.scale(.1)
        
        def shoot(this):
            x = this.pos.x + this.shape.points[1].x
            y = this.pos.y + this.shape.points[1].y
            this.weapon.shoot(x,y,this.v.x,this.v.y,getDir(this.angle))
            
        def destroy(this):
            this.shape.destroy()
            this.lifeBar.destroy()
            if fuelLimit:
                this.fuelBar.destroy()
            this.nameDisplay.destroy()
            Ship.lst.remove(this)
            socketio.emit('destroyed','stuff',room=this.id,namespace='/'+name)
            User.userDict[this.id].score = 0
            updateScoreboard()
            if upgradeType == 'ship builder':
                for part in this.parts:
                    part.destroy()
            else:
                this.engine.destroy()
        
        def updateLife(this):
            this.lifeBar.width = this.lifeBarSize * this.health / this.maxHealth
            
        def updateFuel(this):
            this.fuelBar.width = this.fuelBarSize * this.fuel / this.maxFuel
        
        def hit(this, bullet):
            damage = bullet.v.subtract(this.v).magnitude() * bullet.mass/10
            this.health -= damage
            this.updateLife()
            if this.health <= 0:
                this.destroy()
                User.userDict[bullet.id].score += 1
                if upgradeType == 'simple':
                    User.userDict[bullet.id].ship.upgrades += 1
                    socketio.emit('upgrade',User.userDict[bullet.id].ship.upgrades,room=bullet.id,namespace='/'+name)
                    print(User.userDict[bullet.id].ship.upgrades)
                updateScoreboard()
            print(damage)
            
        @staticmethod
        def moveAll(dt):
            for ship in Ship.lst:
                ship.moveShip(dt)
                
    class UpgradeStation(Ship):
        def __init__(this,x,y,vx,vy,color):
            this.x = x
            this.y = y
            this.pos = Point(x,y)
            this.mass = 1
            this.vx = vx
            this.vy = vy
            this.v = Point(vx,vy)
            this.color = color
            this.shapePoints = [Point(-30,0),Point(0,30),Point(30,0),Point(0,-30)]
            this.shape = Polygon(x,y,this.shapePoints,color)
            
            this.angle = math.pi / 2
            this.turn = 0
            this.throttle = 0
            
            this.parts = []
            this.relativeParts = []
            this.partDict = {'Control':[],'Engines':[],'Fuel tanks':[],'Weapons':[]}
            this.nameDisplay = Point(0,0)
            this.lifeBar = Point(0,0)
            
            Ship.lst.append(this)
            
        def hit(this,bullet):
            pass
            
        def destroy(this):
            this.shape.destroy()
            
            
    
    def getSendAll():
        return {'circles':Circle.getSend(),
                            'polygons':getSend(Polygon),
                            'rectangles':getSend(Rectangle),
                            'text':getSend(Text)}
    
    if name != 'ship-builder':
        fn = ("@app.route('/"+name+"')\n"
            +'def '+name+'():\n'+
            '\treturn render_template("index.html")')
        print(fn)
        #https://stackoverflow.com/questions/12698028/why-is-pythons-eval-rejecting-this-multiline-string-and-how-can-i-fix-it
        exec(fn)
        
        sx = View.width//2
        sy = View.height//2   
        ''' 
        for i in range(-100,100):
            for j in range(-100,100):
                x = i*View.width/5
                y = j*View.height/5
                if Point(x,y).subtract(Point(sx,sy)).magnitude() < View.maxDist: 
                    Circle(x,y, 10, 'yellow')
        '''
        global star
        star = Planet(sx,sy, 0, 0, 75,1000000,'red',None,True)
        
        if upgradeType == 'ship builder':
            print('creating upgrade station...',end='')
            UpgradeStation(View.width//2,View.height//2 + 450, 170,1,'blue')
            print('Done')
            
        def spawnPlanets():
            global star
            for i in range(1,5):
                #d = random.randint(star.r,View.width/2)
                d = 3*star.r + i * 1/2 * View.width/2
                v = (Planet.g*star.mass/d)**.5
                dist = 2*(i%2)-1
                Planet(star.x,star.y+d,v,0,50,100000/5,'green',star)
        spawnPlanets()
        #c = Planet(View.width//2,View.height//2-400, -100, 0, 75,100,'red')
        
        global s
        #s = Ship(View.width//2,View.height//2 - 200, 1,170,0,'blue')
        #Ship(View.width//2,View.height//2 + 200, 1, 170,0,'green')   
        global room 
        @socketio.on('my event', namespace='/'+name)
        def handle_message(message):
            global room
            room = 'main'
            global prevTime
            #print('received message: ' + str(message))
            print('going to send a message now')
            t = time.time()
            dt = t - prevTime[name]
            maxdt = .02
            dt = min(dt,maxdt)
            join_room('main')
            if (dt > .01):
                Ship.moveAll(dt)
                prevTime[name] = t
                emit('update', {'circles':Circle.getSend(),
                                'polygons':getSend(Polygon),
                                'rectangles':0,
                                'text':0},namespace='/'+name)
            # if tab is not open, update not called -> dt very large -> spaceship moves very far from planet
            
        @socketio.on('first start', namespace='/'+name)
        def start(pname, ship=''):
            a = ControlUnit(0,0)
            a.destroy()
            print('===================== starting game '+name+'================================================')
            color = random.choice(['blue','green','white','yellow'])
            if (upgradeType=='ship builder'):
                s = Ship(View.width//2,View.height//2 + 400, 1,170,0,color,request.sid, pname, 
                    ship)
            else:
                s = Ship(View.width//2,View.height//2 + 400, 1,170,0,color,request.sid, pname)
            User(request.sid, s, View(s.x,s.y), pname)
            User.userDict[request.sid].builtShip = ship
            User.userDict[request.sid].shipSet = True
            updateScoreboard()
            join_room('main')
        
        @socketio.on('start again', namespace='/'+name)
        def restart():
            color = random.choice(['blue','green','white','yellow'])
            if (upgradeType=='ship builder'):
                s = Ship(View.width//2,View.height//2 + 400, 1,170,0,color,request.sid, User.userDict[request.sid].name, 
                    User.userDict[request.sid].builtShip)
            else:
                s = Ship(View.width//2,View.height//2 + 400, 1,170,0,color,request.sid, User.userDict[request.sid].name)
            User.userDict[request.sid].ship = s;
            User.userDict[request.sid].score = 0;
        
        @socketio.on('fire engine', namespace='/'+name)
        def updateMotion(value):
            value = min(value,1)
            User.userDict[request.sid].ship.throttle = value*10
            #print('accelerating')
            
        @socketio.on('rotate', namespace='/'+name)
        def rotate(value):
            value = max(min(value,1),-1)
            User.userDict[request.sid].ship.turn = value*.1
            #print('turning')
        
        @socketio.on('shoot', namespace='/'+name)
        def fire():
            User.userDict[request.sid].ship.shoot()
        
        if oreMining:
            @socketio.on('click', namespace='/'+name)
            def deployMiner(x,y):
                print('-------------------checking if valid target-------------------')
                print('x',x,'y',y)
                ship = User.userDict[request.sid].ship
                pt = Point(x,y).add(ship.pos).subtract(Point(View.width/2,View.height/2))
                print('x',pt.x,'y',pt.y)
                for planet in Planet.lst:
                    print('planet x',planet.x,'y',planet.y)
                    if planet.pointIn(pt):
                        OreMiner(ship.pos.x,ship.pos.y,planet)
                        print('creating ore miner')
                        break
        
        @socketio.on('upgrade', namespace='/'+name)
        def upgrade(part):
            ship = User.userDict[request.sid].ship
            if ship.upgrades > 0:
                if part == 'engine':
                    ship.engine.force += .5
                    ship.upgrades -= 1
                    print('engine upgraded')
                    
                elif part == 'weapon bspeed':
                    ship.weapon.bspeed += 50
                    ship.upgrades -= 1
                    print('bspeed increased')
            
        def tick():
            print('running',name)
            while True:
                global room
                global prevTime
                t = time.time()
                dt = t - prevTime[name]
                Ship.moveAll(dt)
                Bullet.moveAll(dt)
                Planet.moveAll(dt)
                if oreMining:
                    OreMiner.moveAll(dt)
                if upgradeType == 'ship builder':
                    pass
                    #print(len(getSend(Polygon)))
                socketio.emit('update', {'circles':Circle.getSend(),
                                    'polygons':getSend(Polygon),
                                    'rectangles':getSend(Rectangle),
                                    'text':getSend(Text)}, namespace='/'+name)
                prevTime[name] = t
                for user in User.userDict.keys():
                    socketio.emit('view',User.userDict[user].ship.pos.getDict(),room=User.userDict[user].id, namespace='/'+name)
                    socketio.emit('score',User.userDict[user].score,room=User.userDict[user].id, namespace='/'+name)
                eventlet.sleep(.01)
        
        #thread = threading.Thread(target=tick)
        #thread.start()
        eventlet.spawn(tick)
        #eventlet.spawn(tick)
    else:
        print('ship builder created')
        global partStrings
        global parts
        partStrings = {
            'Control':['ControlUnit'],
            'Engines':['Basic'],
            'Fuel tanks':['FuelTank'],
            'Weapons':[]}
        parts = {}
        width = 30
        Ycount = 0
        Yspace = (2*View.height/3)/(len(partStrings.keys())+3) #TODO: fix this
        for k in partStrings.keys():
            space = View.width/(len(partStrings[k])+2)
            y = (2*View.height/3) + Ycount * Yspace
            Text(space,y,k,'black','20px Arial')
            count = 2
            for part in partStrings[k]:
                x = count * space
                code = part+'('+str(x)+','+str(y)+')'
                print(code)
                p = eval(code)
                print(p)
                parts[k] = parts.get(k,[])+[p]
                print(parts)
                Text(x,y+10,part,'black','20px Arial')
                count += 1
            Ycount += 1
        @app.route('/ship-builder')
        def shipBuilder():
            return render_template('shipBuilder.html')
            
        @socketio.on('connect',namespace='/ship-builder')
        def shipBuilderConnection():
            User(request.sid,[],None,'')
            User.userDict[request.sid].parts = {
                                        'Control':[ControlUnit(View.width//2,View.height//2)],
                                        'Engines':[],
                                        'Fuel tanks':[],
                                        'Weapons':[]}
            User.userDict[request.sid].selected = None
            emit('update', getSendAll(), namespace='/ship-builder')
                            
        @socketio.on('click', namespace='/ship-builder')
        def click(x,y):
            selected = User.userDict[request.sid].selected
            if selected == None:
                for k in User.userDict[request.sid].parts.keys():
                    for part in (User.userDict[request.sid].parts[k]):
                        if part != None:
                            poly = part.shape
                            #print(x,y,'part',poly.x,poly.y)
                            if poly.ptInPolygon(Point(x,y)):
                                selected = part
                                print('picked up a polygon')
                global parts
                for k in parts.keys():
                    print(k)
                    print(parts[k])
                    for part in parts[k]:
                        #print(part)
                        if part != None:
                            poly = part.shape
                            print(x,y,'part',poly.x,poly.y)
                            if poly.ptInPolygon(Point(x,y)):
                                selected = copy.deepcopy(part)
                                User.userDict[request.sid].parts[k].append(selected)
                                #selected.destroy()
                                print('picked up a polygon from supply')
            else:
                selected = None
                print('dropped a polygon')
            User.userDict[request.sid].selected = selected
            emit('ship code',str(User.userDict[request.sid].parts), namespace='/ship-builder')
        
        def getPartsDict(parts):
            result = []
            for k in parts.keys():
                for part in parts[k]:
                    d = part.shape.getDict()
                    if d != None:
                        result.append(d)
            #print(result)
            return result
        
        @socketio.on('move',namespace='/ship-builder')
        def movePart(x,y):
            selected = User.userDict[request.sid].selected
            if selected != None:
                selected.shape.x = x
                selected.shape.y = y
                #print('moving part',x,y)
            emit('update', {'circles':Circle.getSend(),
                            'polygons':getSend(Polygon)+getPartsDict(User.userDict[request.sid].parts),
                            'rectangles':getSend(Rectangle),
                            'text':getSend(Text)}, namespace='/ship-builder')
            

createGame('simple')
createGame('normal','ship builder',fuelLimit=True, oreMining=True)
createGame('normalnofuellimit','ship builder')
createGame('ship-builder','ship builder')

@app.route('/hello')
def hello():
    return render_template('test.html')

@app.route('/test')
def index():
    return render_template('test.html')
    
@socketio.on('test',namespace='/test')
def test():
    print('received. It works!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    socketio.emit('test',namespace='/test')
    
@socketio.on('connect',namespace='/test')
def connect():
    print('a user connected')

if __name__ == '__main__':
    socketio.run(app)