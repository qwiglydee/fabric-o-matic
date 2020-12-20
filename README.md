
> The project is suspended, 
> because its complexity doesn't fit current state of Blender API
> 
> I'll revive it some day later.

# fabric-o-matic

Nodeware add-on for constructing woven fabric textures in Blender

![big cover](docs/_static/cover.jpg)

The add-on provides set of shader nodes useful to construct procedural textures of various woven fabric.

The main concern is to model fabric structure and to provide maximal procedural flexibility.
(The add-on is not very artist-friendly and does not provide ready plug-and-play textures).




# Installation

Download file `fabricomatic_*.zip` file from 'Releases' section and use 'install' command in Blender.

Unless failed, it will extend 'Add' menu of shader node editor.

# Usage  

There are three ways of using it.

## Using samples library

From menu choose 'Browse library'. 
The Blender UI is weird and you need to click big square to open popup with previews to select one of materials. 
And then confirm it pressing 'OK' button. This will import selected material and insert into current material slot.

Then you can have fun exploring and tweaking it.  

## Using stub

From menu choose 'Stub weavign nodes'. 
This will insert and connect bunch of nodes into current material (or create new material, if missing). 
The nodes produce simple plain weaving with stupid colouring.

Then you can add and replace nodes from 'components' and 'utilities'.

## Using nodes

From menu select 'Weaving components' or 'Utilities' and build everything from scratch.

The main nodes are: 
- `scaling` to scale UV space according to desired thread count;
- one of `weaving` nodes to generate interlacing pattern;
- `strobing` to generate stripes layout according to thickness;
- `overlaying` to combine them all into elevation map and thread mask; 

# Documentation

Rough API documentation of all the nodes is available at [GH pages](https://qwiglydee.github.io/fabric-o-matic/)

In [wiki section](https://github.com/qwiglydee/fabric-o-matic/wiki) I'll put some recipes about using nodes to produce some effects.

