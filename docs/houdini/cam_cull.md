# Frustum cull simulations and moving cameras
When working on heavy simulations, you'll eventually reach the point where you're trying to optimize things to get that extra bit of detail without having to wait for days. Ideally you'd like things go through the farm without someone from system or production yelling at you, or your own workstation going

<figure markdown="span">
    ![Fatal Error](/assets/pages/hou_camcull/fatal_error.jpg){width="90%"}
</figure>

On top of clustering, a very common operation in these situations is camera culling at simulation time.  
Depending on the solver you're using you might opt for a *toNDC-check* or a *volumesample-the-frustum* approach, you name it.  

Unfortunately, camera culling in a solver doesn't really do well in those situations where the simulation must be computed in regions that are currently NOT framed by the camera, but that will eventually be.  
Those regions therefore can't simply be culled, as this would prevent the simulated objects from being present when they are needed (*duh*). 

So how do we keep out-of-frustum stuff simming while still getting rid of it as soon as it leaves the camera?^(1)^ 
{ .annotate }

1. and without using any keyframe, hate those

## Houdini sample scene
Here's a simple scene showing the technique described on this page. Please feel free to download and check it yourself.

[:custom-houdini-badge: Hipfile Download](/assets/projectfiles/houdini/pyro_culling_trail.git_v001.hipnc){.md-button .download-hipfile}

Imagine having to work on something like this:^(1)^ 
{ .annotate }

1.  damn, it looks like trash, more voxels will definitely fix it

<video class="video-center-80" autoplay loop muted playsinline>
    <source src="/assets/pages/hou_camcull/final_shot.webm" type="video/webm">
</video>


This (amazing) shot features:

* a bunch of [smoke plumes]("not ILM™ looking") that need preroll before being framed

* an [explosion]("not quite Michael Bay™ worthy") happening out of camera

* camera traveling a decent distance, then turning around

As I said before, I'd like to camera cull my sims as soon as they're not needed anymore (ie: left behind).  
There are a few ways to achieve what we're looking for.  

!!! example "Fedor's Take"
    My dear deskmate Fedor Koleganov once showed me his approach for these kind of situations.   
    Starting from the current frame, trail the camera frustum forward until the end of the shot range. Make a VDB out of it. Cache one for each frame. Then `volumesample` it at sim time: if the particle/voxel is outside, blast it/deactivate it > done!  
    Given a frame, trailing the camera frustum until the end of the shot returns an active area that covers everything that's going to be needed *"in the future"*, while excluding everything that's already *"gone"*. Pretty cool uh? 

While Fedor's solution is valid, since 80% of my time in the studio consists of arguing with him, I tried to come up with a non-time-dependent version of it. That is to say, I only want to load my culling data once and use that, instead of having to compute a different masking volume for each frame.  
If you couldn't care less, then go with Fedor's approach^(1)^, otherwise keep scrolling to see how we get to this:
{.annotate}

1. he'll be very happy, me on the other hand...
<figure markdown="span">
    ![Pyro camera cull result](/assets/pages/hou_camcull/cam_cull_witness.gif){width="80%"}
</figure>

## Camera frustum trail - `last_frame` utility volume

This solution will also use a camera frustum volume trail.  
To achieve a non-time-dependent solution though, we're not going to use a simple 0-1 masking value. Instead, let's treat the volume as a utility grid where voxels store the *last frame* at which that portion of space was effectively "seen" by the camera. It's pretty straightforward:

- First, we generate a volume grid representing the camera frustum. The volume can be quite low-res as it will simply act as a mask.  
We assign the whole volume a density value of `$F`.  
Now, the region of space seen by the camera at the current frame has a value equal to the current frame (*duh*).

- We then repeat this for each frame of the shot, storing in a final grid the maximum Frame value for each voxel in space. This will effectively give us the last time a certain portion of space was last seen by the camera!  
We can achieve this with a simple sop solver. Inside the solver we compare the current frame and the previous one, using a `vdbcombine` we save the maximum value of each voxel.  

- We then freeze the result at `$FEND + 1` using a `timeshift`and cache that one single frame!
Congrats, you can now use this non-time-dependent cache to perform camera culling on all the sim layer of your setup! 

???note "Viewport visualization"
    The volume will look like absolute garbage in the viewport. This is because the density values will likely be very high, unless your working with a [1; N] frame range. Which is not the case, right? Right. 

    If you want to visualize the "active" area, you can use a Volume Visualizer with Min set to `$F-1` and max set to `$F`.

    <video class="video-center-80" autoplay loop muted playsinline>
        <source src="/assets/pages/hou_camcull/cam_cull_viz.webm" type="video/webm">
    </video>
     

Below you can find the implementation of what I just described. On the next paragraph we'll have a look at a few lines of vex to perform the culling inside a solver.

<figure markdown="span">
![Cam Frustum Trail Utility Volume Tree](/assets/pages/hou_camcull/cam_frust_nodes_all.png){: style="width:80%"}
</figure>

??? quote "Node parameters"
    ``` json
    {
        "frustum_volume": {
            name: "last_frame",
            initial_val: "$F", //Or $FF if you plan on storing subframe data
            dimensions: "From Camera",
            camera: "path/to/your/cam",
            zmin: 0.1,  //Use a meaningful value for your shot
            zmax: 20,   //Use a meaningful value for your shot
            winxmin: -0.1, winxmax: 1.1, //A touch of padding
            winymin: -0.1, winymax: 1.1, //A touch of padding
            uniformsamples: "By Size",
            divsize: 0.5
        },

        "convertvdb1": {
            conversion: "VDB",
            bdbtype: "Integer" //This can be skipped if you want to have subframe data
        },

        "vdbresample1": {
            order: "Nearest",
            mode: "Using Voxel Size Only",
            voxelsize: 0.2,
            linearxform: True //Force Axis Aligned! This is very important, VDB combine will act weird otherwise! 
        },

        "frustum_trail": {
            startframe: 950 //Your camera range start, include preroll if camera anim has some
        }

        "freeze_last": {
            frame: "$FEND + 1" //End of your shot, plus one to avoid disappearing stuff on the last frame
        }
    }

    ```


## Culling - Inside the dopnet

At this point everything is ready, now depending on what you're simulating, you can sample the volume and reset fields/cull points/set attributes.

### Pyro simulation

In a gasfieldwrangle, all the fields that drive the active field need to be set to 0. 
``` c linenums="1" title="Solver Gas Field Wrangle"
float last_frame = volumesample(1, 0, v@P);

if(@Frame > last_frame) {
    f@density = 0;
    f@flame = 0;
}
```

!!!warning "The `vel` field"
    Don't set vel to 0 using this method. 
    This results in the boundary acting similarly to a collider, let the sparse solver handle the culling of the other fields through the building/application of the active mask.

!!!warning "The `active` field"
    I don't recommend setting the `active` field directly, as it needs particular conditions to be work properly.
    The `active` field needs to be a 16x16x16 "full tile" occupancy mask, so messing up with per-voxel 1-0 values will break things.
    Also, depending on the Reset Rule and when you apply the culling operation, you'll likely end up having your active field being recomputed before the solve step.
    
    (FYI: the `active` field is rebuilt after Sourcing and Advection, and before the Forces input operators). 

### Particle simulation (also RBD and vellum)

In a popwrangle, by pointing to the frustum trail path in the Inputs Tab > Input 2 > SOP

``` c linenums="1" title="Solver POP Wrangle"
float last_frame = volumesample(1, 0, v@P);

if(@Frame > last_frame) {
    i@dead = 1;
}
```
