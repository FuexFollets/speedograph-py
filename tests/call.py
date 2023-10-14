import speedograph.collect as sc
import asyncio


async def main():
    collection = sc.Collection("fuexfollets")
    collection.ensure_path()
    await collection.collect(cache_data=True)

if __name__ == '__main__':
    asyncio.run(main())
