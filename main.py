import asyncio

from worker.server.server import connect_to_server

def main():    
    asyncio.run(connect_to_server())
    
if __name__ == "__main__":
    main()
