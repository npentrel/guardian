import asyncio

from viam.module.module import Module
from viam.resource.registry import Registry, ResourceCreatorRegistration
from viam.components.button import Button

from src.models.control import Control


async def main():
    """This function creates and starts a new module instance."""
    Registry.register_resource_creator(
        Button.SUBTYPE,
        Control.MODEL,
        ResourceCreatorRegistration(Control.new, Control.validate_config)
    )
    module = Module.from_args()
    module.add_model_from_registry(Button.SUBTYPE, Control.MODEL)
    await module.start()


if __name__ == "__main__":
    asyncio.run(main())

