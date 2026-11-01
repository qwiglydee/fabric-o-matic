# fabric-o-matic

Computational model of yarn in fabric for real-time procedural texture generation.

The project is in research stage.
Nothing to see yet.

# TODO

## Yarn

Base math for yarn generation

- [x] Generic b-spline stuff
- [x] SDF
    - [x] B(2)ezier 2D segment
    - [x] B(2)spline 2D continuous
- [ ] SCF
    - calculate cylindrical params from SDF
    - recreate 3D half-cylinder solid

## Fibers

Make fiber-level texture with twist.

- [ ] For cylindrical coord mapping
- [ ] Remap for SCF disquance

## Structue

Generation of 3D splines from patterns.

- minimal plausible control points
- manual adjustment of geometry, no bother for UX

Weaving:

- [ ] plain checkerboard
- [ ] twill formula
- [ ] jaquard image

Knitting:

- [ ] plain stockinette/reverse
- [ ] welting (garter)
- [ ] ribbing
- [ ] basket

## Elastic

Build elastic model with cosserat simulation (PyElastic) and fit splines approximation to it.

- Model yarn knots with for all possible knots/cells with natural textile parameters of thickness, stiffness
- Fit approximation to B(2)-splines with some principled parameters
