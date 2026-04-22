import numpy as np
from scipy.optimize import root


def get_cell_center(p1, p2, p3, p4, row, col, num_row, num_col):
    """
    Get the four corners of a sub-quadrant defined by a row and column index.
    """
    # Interpolate along the rows (left-right edges)
    alpha = row / (num_row-1)
    beta = col/(num_col-1)

    # The four corners of the sub-quad
    p_a = interpolate(p1,p4,alpha)
    p_b = interpolate(p2, p3, alpha)
    p_i = interpolate(p_a, p_b, beta)


    return p_i
def interpolate(p_start, p_end, alpha):
    """ Interpolate between two points p_start and p_end based on alpha. """
    return (1 - alpha) * np.array(p_start) + alpha * np.array(p_end)

def bilinear(alpha, beta, p1, p2, p3, p4):
    pa = alpha*p1 + (1-alpha)*p4
    pb = alpha*p2 + (1-alpha)*p3
    return (1-beta)*pa + beta*pb

def solve_alpha_beta(pi, p1, p2, p3, p4):
    def fun(ab):
        a, b = ab
        return bilinear(a, b, p1, p2, p3, p4) - pi

    # initial guess [alpha, beta]
    sol = root(fun, x0=[0.5, 0.5])
    alpha, beta = sol.x
    return alpha, 1-beta


def point_line_dist(p, a, b):
    """
    Perpendicular distance from point p to line segment a→b.
    p, a, b are np.array([x,y]).
    """
    v = b - a
    w = p - a
    # cross2D magnitude
    num = abs(v[0]*w[1] - v[1]*w[0])
    den = np.linalg.norm(v)
    return num/den if den>0 else np.linalg.norm(w)


def bound(x, min_val, max_val):
    return min(max(x, min_val), max_val)

def find_row_col(robot_pos, p1, p2, p3, p4, num_row, num_col):
    rp = np.array(robot_pos)

    # --- find row index ---
    row_dists = []
    for i in range(num_row):
        α = i/(num_row-1)
        A = α*p4 + (1-α)*p1
        B = α*p3 + (1-α)*p2
        row_dists.append(point_line_dist(rp, A, B))
    row = int(np.argmin(row_dists))

    # --- find col index ---
    col_dists = []
    for j in range(num_col):
        β = j/(num_col-1)
        C = β*p2 + (1-β)*p1
        D = β*p3 + (1-β)*p4
        col_dists.append(point_line_dist(rp, C, D))
    col = int(np.argmin(col_dists))

    return row, col
