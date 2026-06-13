# run me to test if the rpc client in gui is working

from sipyco.pc_rpc import Client


def main():
    remote = Client("::1", 3249, "sequence_gui_rpc")
    try:
        remote.print("Hello", "World!", 123)
    finally:
        remote.close_rpc()


if __name__ == "__main__":
    main()
