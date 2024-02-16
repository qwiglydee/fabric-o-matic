# Fabric model

The goal is to build math model for procedural rendering of fabric with yarn-level detail.

That should suppport most common woven and knitted fabric structures:
- weaving:
  - plain
  - twill with various parameters of up/down and shift
- knitting:
  - stockinette
  - reverse stockinette
  - garter
  - rib
  - seed and moss

Final implementation should achieve:
- realistic yarns shape
- smoothness of yarns across the fabric
- it should run in real-time without simulation phases
- artistic control of each separate yarn
- artistic control of ovetall fabric structure on different level of details
- prefer artistic parameters over physiscs

Requirements for math:
- local calculations, based on immediate surrounding of calculated points
- numerically stable computations
- preferring closed-form solutions and avoiding numerical methods
- ideally, avoiding any iterative or recursive calculations

Final target is OpenSL language shaders mapping texure coordinates to surface elevation/displacement or intensity/color.
The shaders supposed to run in a node-controlled environment such as Blender3d.

## Base idea

The base idea is to use splines to model yarn shapes.

The splines should provide at least $C^1$ continuity, so that neighbour segments connect smoothly along with their textures.

## Workflow

1. fabric is formed from regular grid of knots
2. knots determine intersecting segments of yarn aligned with neighbour knots
3. segments of yarn are modelled as fragments spline curves
4. the curves are beveled to produce cylindrical surface in polar coordinates to be textured with fibers

### 1. Patterns

Base grid can be based on UV coords.
For knitting, a loop intersects with 4 other and the grid could be split 2x2 to keep 1 intersection per cell.

To maintain continuity, pattern should provide parameters for neighbour cells, along with all artistic control and added noise.
This seems achievable by combining/dublicating shader nodes.

Irregular patterns can be sampled from a discrete-color raster image, provided it is sampled along with neighbour pixels

### 2. Knots

There are 2 basic knots for weaving and 2 for knitting:
- weaving:
  - weft-facing
  - warp-facing
- knitting:
  - knit stitch (*2 halves)
  - purl stitch (*2 halves)

All of the knots contain 2 arcs, each can be defined by 3 key poinrs: tip of arc and edges.
Resulting points should be appropriate for the yarn model.

The knots processing should align edges to match neighbour knots, and adjust the tips to fit thickness.
The thickness and neighbour knots can be altered by artistic control, so they should not be assumed symmetrical.

### 3. Yarn

Yarn can be modelled by *some kind of* splines, interpolating or approximating key points of knots.

To maintain continuity at the edges, the splines should also take 2 additional points from neighbour knots.
So, it is 5 points per local segment of spline.

To be physically correct according to tension stuff, the splines should be at least 3rd degree.
It might be visually acceptable to approximate it with quadratic splines to simplify calculations.

### 4. Texture

The texture should be mapped to cylinder polar cordinates to produce pipe-like visuals.
The coordinates should either wrap or ideally be continuous at edges of segments.

The polar coordinates are:
- $s$: length along the curve -> texture $u$
- $r$: distance from axis -> texture $v$ for flat mapping
- $a$: angle above horizontal surface -> texture $v$ for cylindrical wrapping

The arclength is nearly impossible to calculate, and it's probably ok to approximate them with curve parameter $t$.

With regular grid lengths of segments in knos are equal and can be mapped to $[0, 1]$.
That comes natural with $t$ approximation.

Main challenge is to find projection (closest) point, which requires solving equation of degree $2d-1$, which is 3 for quadratic and 5 for cubic curves.
The cubic equation is solvable in closed form, though.