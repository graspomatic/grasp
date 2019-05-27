import numpy as np

#constants
ports_x = 7                 # how many ports in x direction
ports_y = 12                # how many ports in y direction
spacing_x = 43.5            # spacing between ports in x direction
spacing_y = 43.5            # spacing between ports in y direction

tl = np.array([268, 9])     # top left x,y position using left arm
tr = np.array([6, 7])       # top right x,y position using left arm
bl = np.array([267.5, 460]) # bottom left x,y position using left arm
br = np.array([5, 459])     # bottom right x,y position using left arm

# calculate angles on the four sides and then find the weighted average (vertical is about 2x the distance of hori)
top_angle =    np.arctan((tr[1]-tl[1])/(tr[0]-tl[0]))
bottom_angle = np.arctan((bl[1]-br[1])/(bl[0]-br[0]))
left_angle =   np.arctan((bl[0]-tl[0])/(tl[1]-bl[1]))
right_angle =  np.arctan((tr[0]-br[0])/(br[1]-tr[1]))

mean_rot = np.mean([top_angle, bottom_angle, left_angle, right_angle, left_angle, right_angle])
mrdeg = round(np.degrees(mean_rot), 2)

if (mean_rot > 0):
    print(f'I think the grid is rotated counter-clockwise {mrdeg} degrees')
else:
    print(f'I think the grid is rotated clockwise {abs(mrdeg)} degrees')


# predict location of adjacent 2 corners based on each of the 4 locations
x_span = spacing_x * (ports_x - 1)
y_span = spacing_y * (ports_y - 1)
# starting with top left
tr_from_tl = np.array([tl[0] - x_span * np.cos(mean_rot), tl[1] - x_span * np.sin(mean_rot)])
print(tr_from_tl)

bl_from_tl = np.array([tl[0] - y_span * np.sin(mean_rot), y_span * np.cos(mean_rot)])
print(bl_from_tl)

