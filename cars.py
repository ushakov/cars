import pygame
import time
import random

class World(object):
    kHorizon = 100
    kCarLength = 4

    def __init__(self):
        self.cars = {}

    def AddCar(self, car):
        self.cars[car.id] = car

    def RemoveCar(self, id):
        del self.cars[id]

    def GetView(self, id):
        x = self.cars[id].GetCoords()
        view = []
        for c in self.cars.values():
            cx = c.GetCoords()
            if abs(x - cx) <= World.kHorizon:
                view.append(c)
        return (0, view)
    
    def CheckCollisions(self):
        if len(self.cars) == 0:
            return
        s = self.cars.values()
        s.sort(key = lambda x : x.GetCoords())
        
        prev = None
        for c in s:
            if prev is not None and c.GetCoords() - prev.GetCoords() < World.kCarLength:
                prev.crashed = True
                c.crashed = True
            prev = c


class Car(object):
    kMaxAccelAt60 = 2
    kMaxAccelAt0 = 10
    kMaxDecel = -10

    def __init__(self, id, x, speed, driver):
        self.id = id
        self.speed = speed
        self.x = x
        self.driver = driver
        self.driver.SetId(id)
        self.set_ctrl = 0
        self.crashed = False

    def MaxAccel(self, speed):
        if speed < 0:
            return self.kMaxAccelAt0
        if speed < 17:
            return (speed * self.kMaxAccelAt60 + (17 - speed) * self.kMaxAccelAt0) / 17
        return self.kMaxAccelAt60

    def DoStep(self, dt, world):
        extforce, view = world.GetView(self.id)
        ctrl = self.driver.Drive(self.x, self.speed, view)

        self.set_ctrl = ctrl

        max_accel = self.MaxAccel(self.speed)
        if ctrl > max_accel:
            ctrl = max_accel
        if ctrl < Car.kMaxDecel:
            ctrl = Car.kMaxDecel

        total_force = extforce + ctrl
        self.speed += total_force * dt
        if self.speed < 0:
            self.speed = 0

        self.x += self.speed * dt

    def GetSpeed(self):
        return self.speed

    def GetCoords(self):
        return self.x

class Runner(object):
    kMaxDistance = 50
    kMinDistance = 20

    def __init__(self):
        self.world = World()
        self.id = 1
        self.far_end = 1000
        dr = WallDriver()
        wall = Car("wall", 200, 0, dr)
        self.world.AddCar(wall)

    def Run(self, dt):
        nearest = None
        for car in list(self.world.cars.values()):
            cx = car.GetCoords()
            if cx > self.far_end:
                self.world.RemoveCar(car.id)
                continue
            if nearest == None or nearest > cx:
                nearest = cx

        if (nearest == None or nearest > Runner.kMaxDistance
            or (nearest > Runner.kMinDistance and random.random() < 0.1)):
            desired_speed = max(10, random.gauss(17,3))
            if desired_speed < 5:
                desired_speed = 5
            dr = CautiousDriver(desired_speed)
            speed = 17
            if random.random() < 0.05:
                speed = 34
            car = Car(self.id, 0, speed, dr)
            self.world.AddCar(car)
            self.id += 1

        for car in self.world.cars.values():
            car.DoStep(dt, self.world)
        self.world.CheckCollisions()

    def GetWorld(self):
        return self.world

class Driver(object):
    def __init__(self):
        self.id = None
        self.msg = ''

    def Drive(self, x, speed, view):
        return 0

    def SetId(self, id):
        self.id = id

class CautiousDriver(Driver):
    kComfortTime = 10
    kMinComfort = 8
    kComfort = 10
    kTimeInterval = 2
    kMinBrake = 0.2

    def __init__(self, desired_speed):
        Driver.__init__(self)
        self.desired_speed = desired_speed
        self.buffer_distance = 8

    def FindNearest(self, x, view):
        nearest = None
        for car in view:
            car_x = car.GetCoords()
            if car_x <= x:
                continue
            if nearest is None or car_x < nearest.GetCoords():
                nearest = car
        return nearest

    def Drive(self, x, speed, view):
        nearest = self.FindNearest(x, view)
        if nearest is None:
            self.msg = 'no-car'
            return self.desired_speed - speed

        d_speed = nearest.GetSpeed() - speed
        dx = nearest.GetCoords() - x

        if dx < CautiousDriver.kMinComfort:
            self.msg = 'near'
            return -1000

        comfort_interval_low = speed * CautiousDriver.kTimeInterval + CautiousDriver.kComfort 
        comfort_interval_high = 2 * speed * CautiousDriver.kTimeInterval + CautiousDriver.kComfort 
        if dx < comfort_interval_low:
            target_ds = (comfort_interval_low - dx) / 3.0
            target_speed = nearest.GetSpeed() - target_ds
            if target_speed > speed:
                self.msg = 'leaving'
                return 0
            self.msg = 'to-2s'
            return target_speed - speed - CautiousDriver.kMinBrake

        if dx < comfort_interval_high:
            self.msg = 'following'
            return d_speed

        if d_speed >= 0:
            self.msg = 'free'
            return 0.5 * (self.desired_speed - speed)

        collision_time = - dx / d_speed
        if collision_time < CautiousDriver.kComfortTime:
            self.msg = 'coll'
            return d_speed / (0.3 * collision_time) - CautiousDriver.kMinBrake

        self.msg = '0'
        return 0

class WallDriver(Driver):
    def __init__(self):
        Driver.__init__(self)

    def Drive(self, x, speed, view):
        return 0

class Visualizer(object):
    def __init__(self):
        pass

    def Visualize(self, world):
        for id, car in world.cars.items():
            print id, car.GetCoords(), car.GetSpeed(),
        print

    def Stop(self):
        pass

class GraphVisualizer(Visualizer):
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((0, 300))
        self.w = self.screen.get_size()[0]
        self.scale = 5
        self.font = pygame.font.SysFont('Arial', 10)

    def Visualize(self, world):
        self.screen.fill((255,255,255))
        self.screen.fill((0,0,0), pygame.Rect(0, 50, self.w, 200))
        for car in world.cars.values():
            x = car.GetCoords()
            scaled = x * self.scale
            if scaled > self.w:
                continue
            car_color = (100, 255, 100)
            if car.crashed:
                car_color = (255, 100, 100)
            self.screen.fill(car_color,
                             pygame.Rect(scaled - 2*self.scale,
                                         150 - self.scale,
                                         4*self.scale,
                                         2*self.scale))
            ctrl_color = (255, 255, 255)
            if car.set_ctrl < Car.kMaxDecel:
                ctrl_color = (255, 100, 100)

            upstr = self.font.render('%.2f' % car.set_ctrl, True, ctrl_color)
            dnstr = self.font.render('%.1f' % car.GetSpeed(), True, (255,255,255))

            self.screen.blit(upstr, (scaled - 2*self.scale, 150-self.scale-15))
            self.screen.blit(dnstr, (scaled - 2*self.scale, 150+self.scale+5))

            msg = self.font.render(car.driver.msg, True, (255,255,255))
            self.screen.blit(msg, (scaled - 2*self.scale, 150+self.scale+15))

        pygame.display.flip()

    def Stop(self):
        pygame.display.quit()

        
if __name__ == '__main__':
    r = Runner()
    v = GraphVisualizer()
    start = prev = time.time()
    wall_removed = False
    while prev - start < 60:
        v.Visualize(r.GetWorld())
        cur = time.time()
        r.Run(cur - prev)
        prev = cur
        if prev - start > 30 and not wall_removed:
            r.GetWorld().RemoveCar("wall")
            wall_removed = True
    v.Stop()
