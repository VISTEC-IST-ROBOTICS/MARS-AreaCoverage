def get_dir_priority(heading):
    dir_priority = ['NORTH','EAST','SOUTH','WEST',] # assume heading EAST
    heading_rotate_num = {
        'EAST':0, # Right
        'SOUTH':1,
        'WEST':2,
        'NORTH':-1 # Left
    }

    def rotate_list(lst, n):
        return lst[n:] + lst[:n]

    dir_priority = rotate_list(dir_priority,heading_rotate_num[heading])
    return dir_priority

for heading in ('NORTH','EAST','WEST','SOUTH'):
    print(heading,get_dir_priority(heading))