class RiotAPIError(Exception):
    """Exception for all errors returned by Riot API"""
    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ServiceConfigurationError(SystemExit):
    """
    Fail-Fast app stop
    """
    pass