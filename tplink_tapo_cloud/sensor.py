"""Sensor Platform for Tp-Link Tapo P110 Smart Plug Integration"""
from __future__ import annotations

from typing import cast, Final
import logging

from homeassistant import config_entries
from homeassistant.const import (
    POWER_WATT,
    ENERGY_WATT_HOUR,
)
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
    )
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    COORDINATOR_DATA_KEY_NAME,
    COORDINATOR_DATA_KEY_DEVICEINFO,
    COORDINATOR_DATA_KEY_ENERGY,
    SENSOR_NAME_ENERGY_TODAY,
    SENSOR_NAME_POWER,
)
from .tapo_coordinator import TapoDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Add sensor entities from a config_entry."""

    _LOGGER.debug("async_setup_entry:enter: entry.entry_id=%s", entry.entry_id)

    # retrieve the TapoDataUpdateCoordinator stored in __init__.async_setup_entry()
    coordinator: Final[TapoDataUpdateCoordinator] = hass.data[DOMAIN][entry.entry_id]

    # list of sensors to be added as entities
    sensors: list[TapoPlugEnergyTodaySensor | TapoPlugCurrentPowerConsumptionSensor] = []

    # append the appropriate entity objects to list of sensors, if sensor is really available
    energy_today = TapoPlugEnergyTodaySensor(coordinator)
    if energy_today.available:
        sensors.append(energy_today)

    power = TapoPlugCurrentPowerConsumptionSensor(coordinator)
    if power.available:
        sensors.append(power)

    async_add_entities(sensors, False) # no need to have an immediate call to update()

    _LOGGER.debug("async_setup_entry:exit: %d entities added for entry.entry_id=%s",
                  len(sensors), entry.entry_id)


class _TapoPlugSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for all Tapo plug sensors."""

    _attr_icon = "mdi:power-socket-eu" # choose a default icon, user can modify

    def __init__(
        self,
        coordinator: TapoDataUpdateCoordinator,
    ) -> None:
        """ Common initialisation."""

        # Pass coordinator to CoordinatorEntity.
        super().__init__(coordinator)

        self.coordinator = coordinator
        self._attr_device_info = self.coordinator.device_info
        self._is_on = False
        self.type = ""
        self.model = ""
        self.unique_device_id = ""
        self._name = ""

        if self.coordinator.data:
            self._is_on = self.coordinator.data[COORDINATOR_DATA_KEY_DEVICEINFO]["device_on"]
            self.type: Final[str] = self.coordinator.data[COORDINATOR_DATA_KEY_DEVICEINFO]["type"]
            self.model: Final[str] = self.coordinator.data[COORDINATOR_DATA_KEY_DEVICEINFO]["model"]
            self.unique_device_id: Final[str] = \
                self.coordinator.data[COORDINATOR_DATA_KEY_DEVICEINFO]["device_id"]

    @property
    def available(self) -> bool:
        """Return if entity is available"""

        # Coordinator data must have energy data, otherwise sensor is treated as not available
        if COORDINATOR_DATA_KEY_ENERGY not in self.coordinator.data:
            return False
        return True

    def _generate_name(self, sensor_name: str) -> str | None:
        """Generate Friendly name of sensor"""

        if not self.coordinator.data:
            return None
        # User can change nickname at any time
        device_name = self.coordinator.data[COORDINATOR_DATA_KEY_NAME]
        return sensor_name.format(device_name)

    def _is_native_value_access_ok(self) -> bool:
        """test if access to coordinator data will be successfull."""

        if not self.coordinator.data:
            _LOGGER.warning("native_value %s: no coordinator data", self._name)
            return False

        if not self.available:
            _LOGGER.warning("native_value %s: sensor not available", self._name)
            return False

        if COORDINATOR_DATA_KEY_ENERGY not in self.coordinator.data:
            _LOGGER.warning("native_value %s: '%s' not available in coordinator data",
                            self._name, COORDINATOR_DATA_KEY_ENERGY)
            return False

        return True


class TapoPlugEnergyTodaySensor(_TapoPlugSensorBase):
    """Representation of a Tapo plug to measure 'todays energy consumption in Wh'."""

    # define constants as class attributes, is shorter than defining property functions
    _attr_device_class: Final = SensorDeviceClass.ENERGY
    _attr_state_class: Final = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement: Final = ENERGY_WATT_HOUR

    def __init__(
        self,
        coordinator: TapoDataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""

        # initialise the base class
        super().__init__(coordinator)

        self._native_value = None

        # generate a unique entity id
        self._attr_unique_id = f"energy-today-{self.unique_device_id}"

    @property
    def name(self) -> str:
        """Return the friendly name of the entity."""

        super_name = super()._generate_name(SENSOR_NAME_ENERGY_TODAY)

        if not super_name:
            # not overwriting self._name
            _LOGGER.warning("name %s: _generate_name failed", self._name)
        else:
            self._name = super_name
        return self._name

    @property
    def native_value(self) -> StateType | None:
        """Return the state (=its value) of the sensor."""

        value = None

        # run through some basic checks first
        access_ok = super()._is_native_value_access_ok()

        if access_ok:
            # today_energy is in Wh, which is equal to ENERGY_WATT_HOUR, no conversion needed
            self._native_value = self.coordinator.data[COORDINATOR_DATA_KEY_ENERGY]["today_energy"]
            unit_of_measurement = getattr(self, "_attr_native_unit_of_measurement")
            _LOGGER.info("native_value %s: %s %s",
                         self._name, self._native_value, unit_of_measurement)
            value = cast(StateType, self._native_value)

        return value


class TapoPlugCurrentPowerConsumptionSensor(_TapoPlugSensorBase):
    """Representation of a Tapo plug to measure 'current power consumption in W'."""

    # define constants as class attributes, is shorter than defining property functions
    _attr_device_class: Final = SensorDeviceClass.POWER
    _attr_state_class: Final = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement: Final = POWER_WATT

    def __init__(
        self,
        coordinator: TapoDataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""

        # initialise the base class
        super().__init__(coordinator)

        self._native_value = None

        # generate a unique entity id
        self._attr_unique_id = f"power-{self.unique_device_id}"

    @property
    def name(self) -> str:
        """Return the friendly name of the entity."""

        super_name = super()._generate_name(SENSOR_NAME_POWER)

        if not super_name:
            # not overwriting self._name
            _LOGGER.warning("name %s: _generate_name failed", self._name)
        else:
            self._name = super_name
        return self._name


    @property
    def native_value(self) -> StateType | None:
        """Return the state (=its value) of the sensor."""

        value = None

        # run through some basic checks first
        access_ok = super()._is_native_value_access_ok()

        if access_ok:
            # current_power is in mW, thus converting it to W (= POWER_WATT)
            milli_watt = self.coordinator.data[COORDINATOR_DATA_KEY_ENERGY]["current_power"]
            self._native_value = milli_watt / 1000.000
            unit_of_measurement = getattr(self, "_attr_native_unit_of_measurement")
            _LOGGER.info("native_value %s: %s %s",
                         self._name, self._native_value, unit_of_measurement)
            value = cast(StateType, self._native_value)

        return value
