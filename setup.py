# from cx_Freeze import setup, Executable
# import zk
#
# setup(name="ZKTeco Local Server",
#       version="0.1",
#       description="ZKTeco Local Server",
#       executables=[Executable("main.py")],
#       requires=['pickledb','zk']
#       )

from cx_Freeze import setup, Executable

setup(name = "ZKTeco Local Server" ,
      version = "0.1" ,
      description = "ZKTeco Local Server" ,
      executables = [Executable("main.py")],
      options = {"build_exe": {"packages": ["zk"]}})