import asyncio
import random
import vlc

from viam.robot.client import RobotClient
from viam.rpc.dial import Credentials, DialOptions
from viam.components.board import Board
from viam.components.camera import Camera
from viam.components.servo import Servo
from viam.services.vision import VisionClient

LIVING_OBJECTS = ["Person", "Dog", "Cat", "Teddy bear"]


async def connect():
    opts = RobotClient.Options.with_api_key(
      # Replace "<API-KEY>" (including brackets) with your robot's api key
      api_key='<API-KEY>',
      # Replace "<API-KEY-ID>" (including brackets) with your robot's api key id
      api_key_id='<API-KEY-ID>'
    )
    return await RobotClient.at_address('guardian-main.vw3iu72d8n.viam.cloud', opts)


async def check_for_living_creatures(detections):
    for d in detections:
        if d.confidence > 0.6 and d.class_name in LIVING_OBJECTS:
            print("detected")
            return d


async def focus_on_creature(creature, width, servo):
    creature_midpoint = (creature.x_max + creature.x_min)/2
    image_midpoint = width/2
    center_min = image_midpoint - 0.2*image_midpoint
    center_max = image_midpoint + 0.2*image_midpoint

    movement = (image_midpoint - creature_midpoint)/image_midpoint
    angular_scale = 20
    print("MOVE BY: ")
    print(int(angular_scale*movement))

    servo_angle = await servo.get_position()
    if (creature_midpoint < center_min or creature_midpoint > center_max):
        servo_angle = servo_angle + int(angular_scale*movement)
        if servo_angle > 180:
            servo_angle = 180
        if servo_angle < 0:
            servo_angle = 0

        if servo_angle >= 0 and servo_angle <= 180:
            await servo.move(servo_angle)

    servo_return_value = await servo.get_position()
    print(f"servo get_position return value: {servo_return_value}")


class LedGroup:
    def __init__(self, group):
        print("group")
        self.group = group

    async def led_state(self, on):
        for pin in self.group:
            await pin.set(on)


async def idle_and_check_for_living_creatures(cam, detector, servo, blue_leds, red_leds, music_player):
    living_creature = None
    while True:
        random_number_checks = random.randint(0, 5)
        if music_player.is_playing():
            random_number_checks = 15
        for i in range(random_number_checks):
            detections = await detector.get_detections_from_camera(cam)
            living_creature = await check_for_living_creatures(detections)
            if living_creature:
                await red_leds.led_state(True)
                await blue_leds.led_state(False)
                if not music_player.is_playing():
                    music_player.play()
                return living_creature
        print("START IDLE")
        await blue_leds.led_state(True)
        await red_leds.led_state(False)
        if music_player.is_playing():
            music_player.stop()
        await servo.move(random.randint(0, 180))


async def main():
    robot = await connect()
    local = Board.from_robot(robot, 'local')
    cam = Camera.from_robot(robot, "cam")
    img = await cam.get_image(mime_type="image/jpeg")
    servo = Servo.from_robot(robot, "servo")
    red_leds = LedGroup([
        await local.gpio_pin_by_name('22'),
        await local.gpio_pin_by_name('24'),
        await local.gpio_pin_by_name('26')
    ])
    blue_leds = LedGroup([
        await local.gpio_pin_by_name('11'),
        await local.gpio_pin_by_name('13'),
        await local.gpio_pin_by_name('15')
    ])

    await blue_leds.led_state(True)

    music_player = vlc.MediaPlayer("guardian.mp3")

    # grab Viam's vision service for the detector
    detector = VisionClient.from_robot(robot, "detector")
    while True:
        # move head periodically left and right until movement is spotted.
        living_creature = await idle_and_check_for_living_creatures(cam, detector, servo, blue_leds, red_leds, music_player)
        await focus_on_creature(living_creature, img.width, servo)
    # Don't forget to close the robot when you're done!
    await robot.close()

if __name__ == '__main__':
    asyncio.run(main())
