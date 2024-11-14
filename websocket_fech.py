import socketio
import asyncio
import json
from image_generator import generate_image



class SimpleMatchClient:
    def __init__(self, base_url: str, match_id: str, guest_user_id: str):

        self.sio = socketio.AsyncClient()
        self.base_url = base_url
        self.match_id = match_id
        self.guest_user_id = guest_user_id

        self.sio.on('connect', self.on_connect)
        self.sio.on(f'match:{match_id}', self.on_match_update)

    async def connect(self):
        """Connect to the WebSocket server."""
        try:
            await self.sio.connect(
                self.base_url,
                auth={'userId': self.guest_user_id},
                socketio_path='api/ws'
            )
            print(f"Connected to WebSocket server")
        except Exception as e:
            print(f"Connection failed: {e}")

    async def disconnect(self):
        """Disconnect from the WebSocket server."""
        await self.sio.disconnect()
        print("Disconnected from server")

    async def on_connect(self):
        print("Connected, joining match room...")
        await asyncio.sleep(2)  # Wait 2 seconds before joining
        await self.sio.emit('joinMatch', {
            'matchId': self.match_id, 
            'guestUserClientId': self.guest_user_id
        })

    async def on_match_update(self, data):
        """Handle match updates."""
        print(f"Match update received: {json.dumps(data, indent=2)}")
        
        generate_image(data, self.match_id)
        # store this data in a file
        # with open("match_data.json", "w") as f:
        #     json.dump(data, f, indent=2)





async def get_score_websocket_and_get_image(match_id):
    print("here")
    base_url = "https://qa.gully6.com"
    guest_user_id = "your_guest_id"  # Replace with your guest ID

    client = SimpleMatchClient(base_url, match_id, guest_user_id)
    
    try:
        await client.connect()
        # Keep connection alive
        await asyncio.sleep(7200)  # Run for 2 hour
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await client.disconnect()
        
    # Read the data from the file
    with open("match_data.json", "r") as f:
        data = json.load(f)
        
        
        
        
        
async def main():
    # Example usage
    # base_url = "https://qa.gully6.com"
    # match_id = input("Enter match ID: ") 
    # guest_user_id = "your_guest_id"  # Replace with your guest ID

    # client = SimpleMatchClient(base_url, match_id, guest_user_id)
    
    # try:
    #     await client.connect()
    #     # Keep connection alive
    #     await asyncio.sleep(7200)  # Run for 1 hour
    # except KeyboardInterrupt:
    #     print("\nShutting down...")
    # finally:
    #     await client.disconnect()
    await get_score_websocket_and_get_image("ilim6xty3")

if __name__ == "__main__":
    asyncio.run(main())
    
    
    

    
    # Return the image path
    # return f"{match_id}.png"