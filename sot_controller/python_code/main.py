from startup import *

rospy.init_node('tf_reem')
listener = tf.TransformListener()
filename = "/tmp/out_from_py.txt"

def transformation(frame_1,frame_2):
    now = rospy.Time.now()
    listener.waitForTransform(frame_1,frame_2, now, rospy.Duration(4.0))
    (xyz,quat) = listener.lookupTransform(frame_1, frame_2, now)
    return {'quat':quat,'xyz':xyz}

def goalDef(frame_1,frame_2,xyz,quat):
    R = quat2mat(quat)
    goal = numpy.matrix([[0 , 0, 0, xyz[0]], [0,  0, 0, xyz[1]], [0, 0, 0, xyz[2]], [0, 0, 0, 1]])
    cur_pose = transformation(frame_1,frame_2)
    R_comp = quat2mat(cur_pose['quat'])
    print R_comp
    goal_r = R * R_comp.transpose()
    goal[0:3,0:3] = goal_r
    return goal

def visDef(frame_1,frame_2,xyz):
    cur_pose = transformation(frame_1,frame_2)
    cur_xyz = cur_pose['xyz'] 
    R_comp = quat2mat(cur_pose['quat'])
    pos = numpy.array([(xyz - cur_xyz)]).T
    axis = R_comp * pos
    theta = math.atan2(axis[1],axis[0])
    alpha = math.atan2(axis[2],axis[1])
    Rz = rotz(-theta)
    Rx = rotx(-alpha)
    goal = numpy.matrix([[0 , 0, 0, cur_xyz[0]], [0,  0, 0, cur_xyz[1]], [0, 0, 0, cur_xyz[2]], [0, 0, 0, 1]])
    goal_r = Rz * Rx
    goal_r = goal_r * R_comp.transpose()
    goal[0:3,0:3] = goal_r.transpose()
    return goal

jointLimits_flag = 1
contact_waist_flag = 1
gaze_flag = 1
rw_flag = 1
lw_flag = 0
com_eq_flag = 1

quat = numpy.array([-0.377,-0.06,-0.142,0.91])
xyz = numpy.array([0.35,-0.3, 1.25])
goal_rw = goalDef("/torso_base_link","/arm_right_tool_link",xyz,quat)
goal_lw = goalDef("/torso_base_link","/arm_left_tool_link",xyz+numpy.array([-0.20,-0.4,0]),quat)
goal_gz = visDef("/torso_base_link","/head_2_link",xyz)

taskRW = MetaTaskKine6d('rw',robot.dynamic,'right-wrist','right-wrist')
taskRW.feature.frame('current')

taskLW = MetaTaskKine6d('lw',robot.dynamic,'left-wrist','left-wrist')
taskLW.feature.frame('current')

taskGAZE = MetaTaskKine6d('gz',robot.dynamic,'gaze','gaze')
taskGAZE.feature.frame('current')

robot.dynamic.upperJl.recompute(0)
robot.dynamic.lowerJl.recompute(0)
taskJL = TaskJointLimits('taskJL')
plug(robot.dynamic.position,taskJL.position)
taskJL.controlGain.value = 1000
taskJL.referenceInf.value = robot.dynamic.lowerJl.value
taskJL.referenceSup.value = robot.dynamic.upperJl.value
taskJL.dt.value = 0.001
taskJL.selec.value = toFlags(range(6,robot.dimension))

taskWT = MetaTaskKine6d('wt',robot.dynamic,'waist','waist')
taskWT.feature.frame('desired')
taskWT.gain.setConstant(1000)

if com_eq_flag:
    taskCOM = MetaTaskKineCom(robot.dynamic)
    robot.dynamic.com.recompute(0)
    taskCOM.featureDes.errorIN.value = robot.dynamic.com.value
    taskCOM.task.controlGain.value = 10 
else:
    featureCOM = FeatureGeneric('featureCom')
    plug(robot.dynamic.com,featureCOM.errorIN)
    plug(robot.dynamic.Jcom,featureCOM.jacobianIN)
    taskCOM = TaskInequality('com')
    taskCOM.add(featureCOM.name)
    taskCOM.selec.value = '011'
    taskCOM.referenceInf.value = (-0.23,-0.24,0)
    taskCOM.referenceSup.value = (0.1,0.24,0)
    taskCOM.dt.value = 0.001
    robot.dynamic.com.recompute(0)
    taskCOM.controlGain.value = 10

if jointLimits_flag:
    push(taskJL)

if contact_waist_flag:
    solver.addContact(taskWT)

if rw_flag:
    push(taskRW)

if lw_flag:
    push(taskLW)

if gaze_flag:
    push(taskGAZE)

push(taskCOM)

time.sleep(5)

if rw_flag:
    gotoNd(taskRW,goal_rw,'111111',100)

if lw_flag:
    gotoNd(taskLW,goal_lw,'111111',100)

if gaze_flag:
    gotoNd(taskGAZE,goal_gz,'111000',10)

time.sleep(15)

err2file(taskRW,filename,"w")
err2file(taskLW,filename,"a")
err2file(taskGAZE,filename,"a")
  
out_file = open("/tmp/joints_limits","w")
count = 0
for elem in robot.device.state.value:
    u = robot.dynamic.upperJl.value[count]
    l = robot.dynamic.lowerJl.value[count]
    count = count + 1
    out_file.write("Rank: " + str(count) +  " state value: " + str(elem) + " lower bound: " + str(l) + "\n")
    out_file.write("Rank: " + str(count) +  " state value: " + str(elem) + " upper bound: " + str(u) + "\n")  

out_file.close()  
  
#Unused code:
"""      
count = 0
for elem in robot.device.state.value:
    u = robot.dynamic.upperJl.value[count]
    l = robot.dynamic.lowerJl.value[count]
    count = count + 1
    if (elem < l):
        out_file.write("Rank: " + str(count) +  " state value: " + str(elem) + " lower bound: " + str(l) + "\n")
    if (elem > u):
        out_file.write("Rank: " + str(count) +  " state value: " + str(elem) + " upper bound: " + str(u) + "\n")
        
robot.dynamic.com.recompute(robot.device.state.time)       
"""





