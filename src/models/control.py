import random
import vlc

from typing import (Any, ClassVar, Dict, Final, List, Mapping, Optional,
                    Sequence, Tuple)

from typing_extensions import Self
from viam.components.button import *
from viam.components.camera import *
from viam.components.board import *
from viam.components.servo import *
from viam.components.component_base import ComponentBase
from typing import cast
from viam.services.vision import *
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import Geometry, ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.utils import ValueTypes
from viam.media.utils.pil import viam_to_pil_image

class LedGroup:
    def __init__(self, group):
        print("group")
        self.group = group

    async def led_state(self, on):
        for pin in self.group:
            await pin.set(on)

class Control(Button, EasyResource):
    # To enable debug-level logging, either run viam-server with the --debug option,
    # or configure your resource/machine to display debug logs.
    LIVING_OBJECTS = ["Person", "Dog", "Cat", "Teddy bear"]
    MODEL: ClassVar[Model] = Model(ModelFamily("naomi", "guardian-logic"), "control")
    music_player: vlc.MediaPlayer = vlc.MediaPlayer("guardian.mp3")
    running: bool = False
    red_leds: LedGroup = None
    blue_leds: LedGroup = None
    width: int = None

    @classmethod
    def new(
        cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ) -> Self:
        """This method creates a new instance of this Button component.
        The default implementation sets the name from the `config` parameter and then calls `reconfigure`.

        Args:
            config (ComponentConfig): The configuration for this resource
            dependencies (Mapping[ResourceName, ResourceBase]): The dependencies (both required and optional)

        Returns:
            Self: The resource
        """
        return super().new(config, dependencies)

    @classmethod
    def validate_config(
        cls, config: ComponentConfig
    ) -> Tuple[Sequence[str], Sequence[str]]:
        req_deps = []
        fields = config.attributes.fields
        if "camera_name" not in fields:
            raise Exception("missing required camera_name attribute")
        elif not fields["camera_name"].HasField("string_value"):
            raise Exception("camera_name must be a string")
        camera_name = fields["camera_name"].string_value
        if not camera_name:
            raise ValueError("camera_name cannot be empty")
        req_deps.append(camera_name)
        if "detector_name" not in fields:
            raise Exception("missing required detector_name attribute")
        elif not fields["detector_name"].HasField("string_value"):
            raise Exception("detector_name must be a string")
        detector_name = fields["detector_name"].string_value
        if not detector_name:
            raise ValueError("detector_name cannot be empty")
        req_deps.append(detector_name)
        if "servo_name" not in fields:
            raise Exception("missing required detector_name attribute")
        elif not fields["servo_name"].HasField("string_value"):
            raise Exception("servo_name must be a string")
        servo_name = fields["servo_name"].string_value
        if not servo_name:
            raise ValueError("servo_name cannot be empty")
        req_deps.append(servo_name)
        # LEDS Configuration
        if "board_name" not in fields:
            raise Exception("missing required board_name attribute")
        elif not fields["board_name"].HasField("string_value"):
            raise Exception("board_name must be a string")
        board_name = fields["board_name"].string_value
        if not board_name:
            raise ValueError("board_name cannot be empty")
        req_deps.append(board_name)
        if "red_leds" not in fields:
            raise Exception("missing required red_leds attribute")
        elif not fields["red_leds"].HasField("list_value"):
            raise Exception("red_leds must be an array")
        red_leds = fields["red_leds"].list_value.values
        if not red_leds or len(red_leds) == 0:
            raise ValueError("red_leds cannot be empty")
        if "blue_leds" not in fields:
            raise Exception("missing required blue_leds attribute")
        elif not fields["blue_leds"].HasField("list_value"):
            raise Exception("blue_leds must be an array")
        blue_leds = fields["blue_leds"].list_value.values
        if not blue_leds or len(blue_leds) == 0:
            raise ValueError("blue_leds cannot be empty")
        return req_deps, []

    def reconfigure(
        self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ):
        camera_name = config.attributes.fields["camera_name"].string_value
        detector_name = config.attributes.fields["detector_name"].string_value
        servo_name = config.attributes.fields["servo_name"].string_value
        board_name = config.attributes.fields["board_name"].string_value

        self.logger.info(f"dependencies: {dependencies}")

        self.camera_name = camera_name
        camera_resource_name = Camera.get_resource_name(camera_name)
        if camera_resource_name not in dependencies:
            raise KeyError(f"Camera service '{camera_name}' not found in "
                           f"dependencies. Available resources: "
                           f"{list[Any](dependencies.keys())}")
        self.camera = cast(Camera, dependencies[camera_resource_name])

        vision_resource_name = VisionClient.get_resource_name(detector_name)
        if vision_resource_name not in dependencies:
            raise KeyError(f"Vision service '{camera_name}' not found in "
                           f"dependencies. Available resources: "
                           f"{list[Any](dependencies.keys())}")
        self.detector = cast(VisionClient, dependencies[vision_resource_name])

        servo_resource_name = Servo.get_resource_name(servo_name)
        if servo_resource_name not in dependencies:
            raise KeyError(f"Servo service '{servo_name}' not found in "
                           f"dependencies. Available resources: "
                           f"{list[Any](dependencies.keys())}")
        self.servo = cast(Servo, dependencies[servo_resource_name])

        board_resource_name = Board.get_resource_name(board_name)
        if board_resource_name not in dependencies:
            raise KeyError(f"Board service '{board_name}' not found in "
                           f"dependencies. Available resources: "
                           f"{list[Any](dependencies.keys())}")
        self.board = cast(Board, dependencies[board_resource_name])

        self.red_leds_list = [str(int(pin.number_value)) for pin in config.attributes.fields["red_leds"].list_value.values]
        self.blue_leds_list = [str(int(pin.number_value)) for pin in config.attributes.fields["blue_leds"].list_value.values]

        return super().reconfigure(config, dependencies)

    async def push(
        self,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> None:
        if not self.blue_leds or not self.red_leds:
            self.blue_leds = LedGroup([
                await self.board.gpio_pin_by_name(pin) for pin in self.blue_leds_list
            ])
            self.red_leds = LedGroup([
                await self.board.gpio_pin_by_name(pin) for pin in self.red_leds_list
            ])

        if not self.width:
            img = await self.camera.get_image(mime_type="image/jpeg")
            pil_frame = viam_to_pil_image(img)
            self.width = pil_frame.width

        if self.running:
            self.running = False
            self.logger.info("Stopping guardian loop")
            self.music_player.stop()
            await self.blue_leds.led_state(False)
            await self.red_leds.led_state(False)
            return
        else:
            self.running = True
            await self.blue_leds.led_state(True)
            self.logger.info("Starting guardian loop")
            return


    async def do_command(
        self,
        command: Mapping[str, ValueTypes],
        *,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Mapping[str, ValueTypes]:
        result = {}
        for name, args in command.items():
            if name == "action" and args == "logic_loop":
                if self.running:
                    await self.idle_and_check_for_living_creatures()
                else:
                    await self.red_leds.led_state(False)
                    await self.blue_leds.led_state(False)
                    if self.music_player.is_playing():
                        self.music_player.stop()
                result["running"] = self.running

        return result

    async def get_geometries(
        self, *, extra: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None
    ) -> Sequence[Geometry]:
        self.logger.error("`get_geometries` is not implemented")
        raise NotImplementedError()

    async def check_for_living_creatures(self, detections):
        for d in detections:
            if d.confidence > 0.6 and d.class_name in self.LIVING_OBJECTS:
                print("detected")
                return d


    async def focus_on_creature(self, creature):
        self.logger.info(f"focusing on creature: {creature}")
        creature_midpoint = (creature.x_max + creature.x_min)/2
        image_midpoint = self.width/2
        center_min = image_midpoint - 0.2*image_midpoint
        center_max = image_midpoint + 0.2*image_midpoint

        movement = (image_midpoint - creature_midpoint)/image_midpoint
        angular_scale = 20
        print("MOVE BY: ")
        print(int(angular_scale*movement))

        servo_angle = await self.servo.get_position()
        if (creature_midpoint < center_min or creature_midpoint > center_max):
            servo_angle = servo_angle + int(angular_scale*movement)
            if servo_angle > 180:
                servo_angle = 180
            if servo_angle < 0:
                servo_angle = 0

            if servo_angle >= 0 and servo_angle <= 180:
                await self.servo.move(servo_angle)

        servo_return_value = await self.servo.get_position()
        print(f"servo get_position return value: {servo_return_value}")


    async def idle_and_check_for_living_creatures(self):
        if not self.blue_leds or not self.red_leds:
            self.blue_leds = LedGroup([
                await self.board.gpio_pin_by_name(pin) for pin in self.blue_leds_list
            ])
            self.red_leds = LedGroup([
                await self.board.gpio_pin_by_name(pin) for pin in self.red_leds_list
            ])
        if not self.width:
            img = await self.camera.get_image(mime_type="image/jpeg")
            pil_frame = viam_to_pil_image(img)
            self.width = pil_frame.width
        living_creature = None
        detections = await self.detector.get_detections_from_camera(self.camera_name)
        living_creature = await self.check_for_living_creatures(detections)
        if living_creature:
            await self.blue_leds.led_state(False)
            await self.red_leds.led_state(True)
            if not self.music_player.is_playing():
                self.music_player.play()
            await self.focus_on_creature(living_creature)
        else:
            await self.blue_leds.led_state(True)
            await self.red_leds.led_state(False)
            if self.music_player.is_playing():
                self.music_player.stop()
            # only move the servo sometimes
            if random.randint(0, 100) < 10:
                await self.servo.move(random.randint(0, 180))
        return living_creature