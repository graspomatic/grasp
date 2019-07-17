import numpy as np
import redis
import json

#constants
ports_x = 7                 # how many ports in x direction
ports_y = 12                # how many ports in y direction
spacing_x = 43.5            # spacing between ports in x direction
spacing_y = 43.5            # spacing between ports in y direction

# DO NOT USE LIST -- spaces that cant be used
DNU = np.array([[5, 3], [5, 4], [9, 3], [9, 4]])

# measured values when in office
# tl = np.array([268, 9])     # top left x,y position using left arm
# tr = np.array([6.5, 7])     # top right x,y position using left arm
# bl = np.array([267, 487])   # bottom left x,y position using left arm
# br = np.array([4, 486])     # bottom right x,y position using left arm

# measured values when in psycho room
# tl = np.array([267, 12])     # top left x,y position using left arm
# tr = np.array([6, 9.5])     # top right x,y position using left arm
# bl = np.array([266.5, 489.5])   # bottom left x,y position using left arm
# br = np.array([5, 487.5])     # bottom right x,y position using left arm

tl = np.array([266.5, 10.7])     # top left x,y position using left arm
tr = np.array([6.25, 9])     # top right x,y position using left arm
bl = np.array([265.8, 488.7])   # bottom left x,y position using left arm
br = np.array([4.6, 486.7])     # bottom right x,y position using left arm

# tlr = np.array([325, 9])     # top left x,y position using right arm
# trr = np.array([64, 7])     # top right x,y position using right arm
# blr = np.array([323.5, 486.5])   # bottom left x,y position using right arm
# brr = np.array([62, 485.5])     # bottom right x,y position using right arm
#
# arm_offset = np.array([57.3, -0.3])



# calculate angles on the four sides and then find the weighted average (vertical is about 2x the distance of hori)
top_angle =    np.arctan((tr[1]-tl[1])/(tr[0]-tl[0]))
bottom_angle = np.arctan((bl[1]-br[1])/(bl[0]-br[0]))
left_angle =   np.arctan((bl[0]-tl[0])/(tl[1]-bl[1]))
right_angle =  np.arctan((tr[0]-br[0])/(br[1]-tr[1]))

mean_rot = np.mean([top_angle, bottom_angle, left_angle, right_angle, left_angle, right_angle])
print(top_angle)
print(bottom_angle)
print(left_angle)
print(right_angle)
mrdeg = round(np.degrees(mean_rot), 2)

if (mean_rot > 0):
    print(f'I think the grid is rotated counter-clockwise {mrdeg} degrees')
else:
    print(f'I think the grid is rotated clockwise {abs(mrdeg)} degrees')


# predict location of top left corner based on the other 3 locations
x_span = spacing_x * (ports_x - 1)
y_span = spacing_y * (ports_y - 1)

tl_from_tr = np.array([tr[0] + x_span * np.cos(mean_rot), tr[1] + x_span * np.sin(mean_rot)])
tl_from_bl = np.array([bl[0] + y_span * np.sin(mean_rot), bl[1] - y_span * np.cos(mean_rot)])
ang = np.arctan(x_span/y_span) + mean_rot      #angle from
hyp = np.sqrt(x_span**2+y_span**2)              # distance from one corner to the other
tl_from_br = np.array([br[0] + hyp * np.sin(ang), br[1] - hyp * np.cos(ang)])

# calculate new top left position
new_tl_x = np.mean([tl[0], tl[0], tl_from_bl[0], tl_from_tr[0], tl_from_br[0]])
new_tl_y = np.mean([tl[1], tl[1], tl_from_bl[1], tl_from_tr[1], tl_from_br[1]])
new_tl = np.array([np.round(new_tl_x, 1), np.round(new_tl_y, 1)])


## now we have the tested grid rotation, a seed value for the top left, and the layout and spacing of our grid
##      generate the empty 3d array

# make a rotation matrix
c,s = np.cos(-mean_rot), np.sin(-mean_rot)
R = np.array(((c,-s),(s,c)))

# initialize the panel
panel = np.zeros((ports_y, ports_x, 3))

# calculate each position
for i in range(ports_y):          # for each row
    for ii in range(ports_x):     # for each column
        unrotated = np.array([ii * spacing_x, i * spacing_y])
        rotated = np.dot(unrotated, R.T)
        #check if this is supposed to be a blank spot
        if np.array([np.isin(DNU[:, 0], i), np.isin(DNU[:, 1], ii)]).all(axis=0).any():
            panel[i, ii, 0] = 99999
        else:
            panel[i, ii, 0] = 0
        panel[i, ii, 1] = round(new_tl[0] - rotated[0], 1)
        panel[i, ii, 2] = round(new_tl[1] + rotated[1], 1)

#panel[11,6,:] returns [  0.    4.8 486.1] for the bottom right

print(panel)

r = redis.Redis(host='localhost', port=6380, db=0)
try:
    p_old = np.array(json.loads(r.get('panel')))
    print(p_old.size)
except:
    print('panel not found')






panelJSON = json.dumps(panel.tolist())
#r.set('panel', panelJSON)
