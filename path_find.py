import numpy as np

class path_find():
    def __init__(self):
        # self.panel = np.array([[[1, 10., 10.], [2, 20., 10.], [3, 30., 10.]],
        #                   [[0, 10., 20.], [5, 20., 20.], [6, 30., 20.]],
        #                   [[0, 10., 30.], [8, 20., 30.], [9, 30., 30.]]])

        # self.right_offset = np.array([12, 1])  # x-y offset for right arm re: left arm



        # get arm_offset



        self.mid_point = np.array([20, 18])  # when only putting away something, aim for this spot

        # self.empties = self.find_empty_spots(self.panel)

    def distance(self, a, b):
        dif = np.subtract(a, b)
        return np.sqrt(dif.dot(dif))

    def find_empty_spots(self, panel):
        empty_spots = panel[:, :, 0] == 0
        empty_coords = panel[empty_spots]
        return empty_coords[:,1:]

    def change_panel_entry(self, panel, x, y, new_val, empties):
        loc = np.where(np.logical_and(panel[:, :, 1] == x, panel[:, :, 2] == y))
        panel[loc[0][0], loc[1][0], 0] = new_val
        empties = self.find_empty_spots(panel)
        print(panel)
        print(empties)
        return panel, empties

    def find_nearest(self, ref, empties):
        # find empty spot nearest reference
        dist_list = []
        for i in range(np.ma.size(empties, 0)):
            dist_list.append(self.distance(ref, empties[i]))
        val, idx = min((val, idx) for (idx, val) in enumerate(dist_list))
        return empties[idx]

    def find_nearest_pair(self, empties, right_offset):
        shortest = np.array([np.array([0, 0]), np.array([0, 0]), 1000000])
        for i in empties:
            for ii in empties:
                if not np.array_equal(i, ii):
                    # if we're here, we know we have two different grid locations
                    d = self.distance(i, ii - right_offset)
                    if d < shortest[2]:
                        shortest = [i, ii - right_offset, d]
        return shortest

    def get_address(self, panel, id, offset):
        if id < 1:
            return 0

        ids = panel[:, :, 0]                # get all the ids on the panel
        ind = np.where(ids == id)           # index of requested object
        if np.size(ind) == 0:
            return 0
        else:
            row = panel[ind[0][0], [ind[1][0]]] # row for this object
            address = row[0][1:] - offset
            return address

    def plan_path(self, drop, pick, panel, right_offset):

        # error checking
        if not isinstance(drop, list):
            print(type(drop))
            print('drop needs to be a list')
            return 0
        if drop[0] < 0 or drop[1] < 0:
            print('drop needs to be a list of two non-negative ints')
            return 0
        if not isinstance(pick, list):
            print('pick needs to be a list')
            return 0
        if pick[0] < 0 or pick[1] < 0:
            print('pick needs to be a list of two non-negative ints')
            return 0
        if pick[0] > 0 and pick[0] == pick[1]:
            print('youre asking for the same object on two arms!')
            return 0
        if pick[0] and not np.any(panel[:, :, 2] == pick[0]) and pick[0] not in drop:
            print('we dont have access to the object requested on left')
            return 0
        if pick[1] and not np.any(panel[:, :, 2] == pick[1]) and pick[1] not in drop:
            print('we dont have access to the object requested on right')
            return 0
        if drop[0] > 0 and drop[0] == drop[1]:
            print('youre trying to drop off two of the same objects')
            return 0
        if np.any(panel[:, :, 0] == drop[0]) or np.any(panel[:, :, 0] == drop[1]):
            print('youre trying to drop off an object thats already on the panel')
            return 0


        d_num = np.count_nonzero(drop)
        p_num = np.count_nonzero(pick)
        empties = self.find_empty_spots(panel)

        if d_num == 0 and p_num == 0:
            print('you didnt give me anything to do')
            return 0

        # could adjust in future to allow for working with only one open spot
        if d_num > np.shape(empties)[0]:
            print('we dont have enough space to put those away')
            return 0

        orders = []

        # handle special case of wanting an object we're already holding
        if pick[0] > 0 and pick[0] in drop or pick[1] > 0 and pick[1] in drop:
            pair = self.find_nearest_pair(empties, right_offset)

            if drop[0]:
                orders.append(np.array([['d'], [0], pair[0]]))  # add this location to list
                panel, empties = self.change_panel_entry(panel, pair[0][0], pair[0][1], drop[0], empties)  # update panel

            if drop[1]:
                orders.append(np.array([['d'], [1], pair[1]]))  # add this location to list
                panel, empties = self.change_panel_entry(panel, pair[1][0] + right_offset[0], pair[1][1] + right_offset[1], drop[1], empties)  # update panel

            if pick[0]:
                add = self.get_address(panel, pick[0], np.array([0, 0]))
                orders.append(np.array([['p'], [0], add]))  # add this location to list
                panel, empties = self.change_panel_entry(panel, add[0], add[1], 0, empties)  # update panel

            if pick[1]:
                add = self.get_address(panel, pick[1], right_offset)
                orders.append(np.array([['p'], [1], add]))  # add this location to list
                panel, empties = self.change_panel_entry(panel, add[0] + right_offset[0], add[1] + right_offset[1], 0, empties)  # update panel

        else:                   # we know that the required objects are on the board
            if drop[0]:         # if we need to drop an object from the left arm
                if pick[0]:
                    add = self.get_address(panel, pick[0], np.array([0, 0]))
                elif pick[1]:
                    add = self.get_address(panel, pick[1], right_offset)
                else:
                    add = self.mid_point

                xy = self.find_nearest(add, empties)                             # find empty spot
                print(xy)
                orders.append(np.array([['d'], [0], xy]))                       # add this location to list
                panel, empties = self.change_panel_entry(panel, xy[0], xy[1], drop[0], empties)    # update panel

            if pick[0]:         # if we need to pick up an object on the left arm
                add = self.get_address(panel, pick[0], np.array([0, 0]))
                print(add)
                orders.append(np.array([['p'], [0], add]))                      # add this location to list
                panel, empties = self.change_panel_entry(panel, add[0], add[1], 0, empties)        # update panel

            if drop[1]:         # if we need to drop off an object with the right arm
                if pick[1]:     # and if we need to pick up and object with the right arm
                    add = self.get_address(panel, pick[1], right_offset)
                    xy = self.find_nearest(add, empties - right_offset)  # find empty spot

                    orders.append(np.array([['d'], [1], xy]))  # add this location to list
                    panel, empties = self.change_panel_entry(panel, xy[0] + right_offset[0], xy[1] + right_offset[1], drop[1], empties)  # update panel
                    empties = self.find_empty_spots(panel)  # update empties

                else:   # we need to drop off right, but not pick up anything else
                    xy = self.find_nearest(self.mid_point, empties - right_offset)  # find empty spot
                    orders.append(np.array([['d'], [1], xy]))  # add this location to list
                    panel, empties = self.change_panel_entry(panel, xy[0] + right_offset[0], xy[1] + right_offset[1], drop[1], empties)  # update panel

            if pick[1]:
                add = self.get_address(panel, pick[1], right_offset)
                orders.append(np.array([['p'], [1], add]))  # add this location to list
                panel, empties = self.change_panel_entry(panel, add[0] + right_offset[0],
                add[1] + right_offset[1], 0, empties)  # update panel


        return panel, orders






