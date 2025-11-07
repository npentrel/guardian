# Module guardian-logic

## A Guardian that Tracks Pets using a Pi, Camera, and Servo

In the run up to the new Zelda release, I realized you can build a stationary guardian robot with a servo and a camera. Adding a bit of machine learning, you can then make the guardian detect objects or people or pets and follow them around by rotating its head. Luckily, I am not the first one to have the idea to build a guardian and there was already a brilliant guardian 3D model on Thingiverse with space for LEDs and a servo.

I've written up a [tutorial](https://www.instructables.com/Print-Paint-and-Program-a-Guardian-to-Track-Humans/) where I walk you through the steps to build your own functional guardian with a servo, a camera, some LEDs and the ML Model service and vision service.

Here’s a video of the finished guardian detecting me:

[![Finished guardian project](https://github.com/npentrel/guardian/assets/5212232/050719b5-b8f7-4813-b812-b314bbe82845)](https://player.vimeo.com/video/852973061?badge=0&amp;autopause=0&amp;player_id=0&amp;app_id=58479)

Here's a video of the guardian following my dog around:
[![Ernie and the Guardian](https://github.com/npentrel/guardian/assets/5212232/42bd0501-ad4f-450f-ac2e-c0db525d7d05)](https://player.vimeo.com/video/852971649?badge=0&amp;autopause=0&amp;player_id=0&amp;app_id=58479)

## Model naomi:guardian-logic:control

Button that starts guardian logic.

### Configuration

The following attribute template can be used to configure this model:

```json
{
  "camera_name": "cam",
  "detector_name": "detector",
  "servo_name": "servo",
  "board_name": "local",
  "red_leds": [
    22,
    24,
    26
  ],
  "blue_leds": [
    11,
    13,
    15
  ]
}
```

### DoCommand

Run the logic periodically.

```json
{
  "action": "logic_loop"
}
```
