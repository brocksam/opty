"""
Bicycle Counter Steering
========================

Objectives
----------

- Demonstrate using kinematic inputs as the unknown trajectories.

"""
from opty import Problem
from opty.utils import MathJaxRepr
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import sympy as sm
import sympy.physics.mechanics as me

# %%
# Specify the equations of motion.
m, h, a, b, v, g, I1, I2, I3 = sm.symbols('m, h a, b, v, g, I1, I2, I3',
                                          real=True)
dt = sm.symbols('dt', real=True)

delta, deltadot, theta, thetadot, x, y, psi = me.dynamicsymbols(
    'delta, deltadot, theta, thetadot, x, y, psi')
t = me.dynamicsymbols._t

eom = sm.Matrix([
    theta.diff(t) - thetadot,
    (I1 + m*h**2)*thetadot.diff(t) +
    (I3 - I2 - m*h**2)*(v*sm.tan(delta)/b)**2*sm.sin(theta)*sm.cos(theta) -
    m*g*h*sm.sin(theta) +
    m*h*sm.cos(theta)*(a*v/b/sm.cos(delta)**2*deltadot +
                       v**2/v*sm.tan(delta)),
    x.diff(t) - v*sm.cos(psi),
    y.diff(t) - v*sm.sin(psi),
    psi.diff(t) - v/b*sm.tan(delta),
    delta.diff(t) - deltadot,
])

MathJaxRepr(eom)

# %%
# Set up the time discretization.
num_nodes = 201
duration = (num_nodes - 1)*dt

# %%
# Provide some reasonably realistic values for the constants.
par_map = {
    I1: 9.2,  # kg m^2
    I2: 11.0,  # kg m^2
    I3: 2.8,  # kg m^2
    a: 0.5,  # m
    b: 1.0,  # m
    g: 9.81,  # m/s^2
    h: 1.0,  # m
    m: 87.0,  # kg
    v: 5.0,  # m/s
}

state_symbols = (theta, thetadot, x, y, psi, delta)


# %%
# Specify the objective function and form the gradient.
# Minimize the time required to go from the start state to the final state.
def objective(free):
    """Return h (always the last element in the free variables)."""
    return free[-1]


def gradient(free):
    """Return the gradient of the objective."""
    grad = np.zeros_like(free)
    grad[-1] = 1.0
    return grad


# %%
# Specify the symbolic instance constraints, i.e. initial and end conditions.
instance_constraints = (
    x.func(0*h),
    y.func(0*h),
    psi.func(0*h),
    delta.func(0*h),
    theta.func(0*h),
    thetadot.func(0*h),
    theta.func(duration),
    delta.func(duration),
    psi.func(duration) - np.deg2rad(90.0),
    thetadot.func(duration),
)

# %%
# Add some physical limits to some variables.
bounds = {
    psi: (np.deg2rad(-180.0), np.deg2rad(180.0)),
    theta: (np.deg2rad(-45.0), np.deg2rad(45.0)),
    delta: (np.deg2rad(-45.0), np.deg2rad(45.0)),
    deltadot: (np.deg2rad(-200.0), np.deg2rad(200.0)),
    thetadot: (np.deg2rad(-200.0), np.deg2rad(200.0)),
    dt: (0.001, 0.5),
}

# %%
# Create the optimization problem and set any options.
prob = Problem(objective, gradient, eom, state_symbols, num_nodes, dt,
               known_parameter_map=par_map,
               instance_constraints=instance_constraints, bounds=bounds,
               time_symbol=t, backend='numpy')

# %%
# Give some rough estimates for the x and y trajectories.
initial_guess = 1e-10*np.ones(prob.num_free)

# %%
# Find the optimal solution.
solution, info = prob.solve(initial_guess)

# %%
# Plot the optimal state and input trajectories.
_ = prob.plot_trajectories(solution)

# %%
# Plot the constraint violations.
_ = prob.plot_constraint_violations(solution)

# %%
# Plot the objective function as a function of optimizer iteration.
_ = prob.plot_objective_value()

# %%
xs, us, ps, dt_val = prob.parse_free(solution)


def points(x):
    """
    Parameters
    ==========
    x : array_like, shape(n, N)

    Returns
    =======
    coordinates : ndarray, shape(N, 7, 3)

    """
    coordinates = np.empty((x.shape[1], 7, 3))

    for i, xi in enumerate(x.T):

        theta, thetadot, x, y, psi, delta = xi

        rear_contact = np.array([x, y, 0.0])
        com_on_ground = rear_contact + np.array([par_map[a]*np.cos(psi),
                                                par_map[a]*np.sin(psi),
                                                0.0])
        com = com_on_ground + np.array([par_map[h]*np.sin(theta)*np.sin(psi),
                                        par_map[h]*np.sin(theta)*np.cos(psi),
                                        par_map[h]*np.cos(theta)])
        front_contact = rear_contact + np.array([par_map[b]*np.cos(psi),
                                                par_map[b]*np.sin(psi),
                                                0.0])
        front_steer = front_contact + np.array([0.2*np.cos(delta + psi),
                                                0.2*np.sin(delta + psi),
                                                0.0])
        rear_steer = front_contact + np.array([-0.2*np.cos(delta + psi),
                                               -0.2*np.sin(delta + psi),
                                               0.0])
        coordinates[i] = np.vstack((rear_contact, com_on_ground, com,
                                    com_on_ground, front_contact, front_steer,
                                    rear_steer))
    return coordinates


coordinates = points(xs)


def frame(i):

    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')

    x, y, z = coordinates[i].T

    bike_lines, = ax.plot(x, y, z,
                          color='black',
                          marker='o', markerfacecolor='blue', markersize=4)
    rear_path, = ax.plot(coordinates[:i, 0, 0],
                         coordinates[:i, 0, 1],
                         coordinates[:i, 0, 2])
    front_path, = ax.plot(coordinates[:i, 4, 0],
                          coordinates[:i, 4, 1],
                          coordinates[:i, 4, 2])

    ax.set_xlim((0.0, 4.0))
    ax.set_ylim((-1.0, 3.0))
    ax.set_zlim((0.0, 4.0))
    ax.set_xlabel(r'$x$ [m]')
    ax.set_ylabel(r'$y$ [m]')
    ax.set_zlabel(r'$z$ [m]')

    return fig, bike_lines, rear_path, front_path


fig, bike_lines, rear_path, front_path = frame(0)


def animate(i):
    x, y, z = coordinates[i].T
    bike_lines.set_data_3d(x, y, z)
    rear_path.set_data_3d(coordinates[:i, 0, 0],
                          coordinates[:i, 0, 1],
                          coordinates[:i, 0, 2])
    front_path.set_data_3d(coordinates[:i, 4, 0],
                           coordinates[:i, 4, 1],
                           coordinates[:i, 4, 2])


ani = animation.FuncAnimation(fig, animate, range(num_nodes),
                              interval=int(dt_val*1000))

plt.show()
