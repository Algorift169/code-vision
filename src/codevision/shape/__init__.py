from .arrow import Arrow
from .api_gateway import ApiGateway
from .authentication import Authentication
from .authorization import Authorization
from .cache import Cache
from .client import Client
from .connector import Connector
from .delay import Delay
from .desktop_application import DesktopApplication
from .encryption import Encryption
from .event_bus import EventBus
from .extract import Extract
from .firewall import Firewall
from .hard_drive import HardDrive
from .input_output import InputOutput
from .internal_storage import InternalStorage
from .load_generator import LoadGenerator
from .log_collector import LogCollector
from .magnetic_disk import MagneticDisk
from .manual_input import ManualInput
from .manual_operation import ManualOperation
from .memory import Memory
from .merge import Merge
from .message_broker import MessageBroker
from .microservice import Microservice
from .monitoring import Monitoring
from .mobile_device import MobileDevice
from .network import Network
from .notification import Notification
from .off_page_connector import OffPageConnector
from .predefined_process import PredefinedProcess
from .preparation import Preparation
from .process import Process
from .router import Router
from .sort import Sort
from .subprocess_shape import Subprocess
from .stored_data import StoredData
from .switch import Switch
from .tape_storage import TapeStorage
from .terminal import Terminal
from .web_browser import WebBrowser
from .base import DiagramShape


SHAPES: tuple[DiagramShape, ...] = (
    Process(),
    Subprocess(),
    InputOutput(),
    Terminal(),
    PredefinedProcess(),
    ManualInput(),
    ManualOperation(),
    Preparation(),
    Connector(),
    OffPageConnector(),
    Delay(),
    Merge(),
    Extract(),
    Sort(),
    StoredData(),
    InternalStorage(),
    TapeStorage(),
    MagneticDisk(),
    HardDrive(),
    Memory(),
    Cache(),
    ApiGateway(),
    Microservice(),
    Client(),
    WebBrowser(),
    MobileDevice(),
    DesktopApplication(),
    Firewall(),
    Router(),
    Switch(),
    Network(),
    LoadGenerator(),
    MessageBroker(),
    EventBus(),
    Notification(),
    Authentication(),
    Authorization(),
    Encryption(),
    Monitoring(),
    LogCollector(),
    Arrow(),
)

__all__ = ["DiagramShape", "SHAPES"]
