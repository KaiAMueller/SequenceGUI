from .Event import Event


class RPCEvent(Event):

    def __init__(self, time, duration, device, name, args, kargs):
        """RPC Event constructor"""
        Event.__init__(self, time=time, duration=duration, device=device)
        self.name = name
        self.args = args
        self.args_string = (f'"{self.name}", ' + "".join([f"{str(arg)}, " if type(arg) is not str else f'"{arg}", ' for arg in args]))[:-2]
        self.kargs_string = ("".join([f'{k}="{str(v)}", ' if type(v) is not str else f'{k}="{v}", ' for k, v in kargs.items()]))[:-2]

    def clone(self):
        return type(self)(
            time=self.time,
            duration=self.duration,
            device=self.device,
            name=self.name,
            args=self.args,
        )

    def generatePrepareCode(self):
        return None

    def generateRunCode(self):
        return f"""
        self.core.wait_until_mu(now_mu())
        self.{self.device.name}.run({self.args_string}, {self.kargs_string})"""
