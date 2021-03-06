from robots import loadTalosLegs
from scipy.optimize import fmin_slsqp
import pinocchio
from pinocchio.utils import *
from numpy.linalg import norm,inv,pinv,eig,svd

m2a = lambda m: np.array(m.flat)
a2m = lambda a: np.matrix(a).T

robot   = loadTalosLegs()
robot.initDisplay(loadModel=True)

class OptimProblem:
    def __init__(self,rmodel,rdata,gview=None):

        self.rmodel = rmodel
        self.rdata = rdata

        self.refL = pinocchio.SE3(eye(3), np.matrix([ 0., .3, 0.]).T )
        self.idL = rmodel.getFrameId('left_sole_link')  # ID of the robot object to control

        self.refR = pinocchio.SE3(eye(3), np.matrix([ 0., -.3, 0.]).T )
        self.idR = rmodel.getFrameId('right_sole_link')# ID of the robot object to control

        self.refQ = rmodel.neutralConfiguration

        self.initDisplay(gview)

        self.neq = 12
        self.eq = np.zeros(self.neq)
        self.Jeq = np.zeros([self.neq, self.rmodel.nv])

        # configurations are represented as velocity integrated from this point.
        self.q0 = rmodel.neutralConfiguration

    def vq2q(self,vq):   return pinocchio.integrate(self.rmodel,self.q0,vq)
    def q2vq(self,q):    return pinocchio.difference(self.rmodel,self.q0,q)
        
    def cost(self,x):
        q = self.vq2q(a2m(x))
        self.residuals = m2a(pinocchio.difference(self.rmodel,self.refQ,q)[6:])
        return sum( self.residuals**2 )
        
    def constraint_leftfoot(self,x,nc=0):
        q = self.vq2q(a2m(x))
        pinocchio.forwardKinematics(self.rmodel,self.rdata,q)
        pinocchio.updateFramePlacements(self.rmodel,self.rdata)
        refMl = self.refL.inverse()*self.rdata.oMf[self.idL]
        self.eq[nc:nc+6] = m2a(pinocchio.log(refMl).vector)
        return self.eq[nc:nc+6].tolist()

    def constraint_rightfoot(self,x,nc=0):
        q = self.vq2q(a2m(x))
        pinocchio.forwardKinematics(self.rmodel,self.rdata,q)
        pinocchio.updateFramePlacements(self.rmodel,self.rdata)
        refMr = self.refR.inverse()*self.rdata.oMf[self.idR]
        self.eq[nc:nc+6] = m2a(pinocchio.log(refMr).vector)
        return self.eq[nc:nc+6].tolist()

    def constraint(self,x):
        self.constraint_rightfoot(x,0)
        self.constraint_leftfoot(x,6)
        return self.eq.tolist()
    
    # --- BLABLA -------------------------------------------------------------
    def initDisplay(self,gview):
        if gview is None: return 
        self.gview = gview
        self.gobjR = "world/targetR"
        self.gobjL = "world/targetL"
        self.gview.addBox(self.gobjR,.1,.03,.03,[1,0,0,1])
        self.gview.addBox(self.gobjL,.1,.03,.03,[0,1,0,1])
        self.gview.applyConfiguration(self.gobjR,se3ToXYZQUAT(self.refR))
        self.gview.applyConfiguration(self.gobjL,se3ToXYZQUAT(self.refL))
        self.gview.refresh()

    def callback(self,x):
        import time
        q = self.vq2q(a2m(x))
        robot.display(q)
        time.sleep(1e-1)


pbm = OptimProblem(robot.model,robot.data,robot.viewer.gui)
pbm.refQ = robot.q0.copy()

x0  = m2a(pbm.q2vq(robot.q0))
result = fmin_slsqp(x0       = x0,
                    func     = pbm.cost,
                    f_eqcons = pbm.constraint,
                    callback = pbm.callback)
qopt = pbm.vq2q(a2m(result))
