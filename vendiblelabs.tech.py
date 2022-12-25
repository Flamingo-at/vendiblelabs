import asyncio
import aiohttp

from re import findall
from web3.auto import w3
from loguru import logger
from aiohttp import ClientSession


async def create_email(client: ClientSession):
    try:
        response = await client.get("https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1")
        email = (await response.json())[0]
        if '@qiott.com' in email:
            return await create_email(client)
        return email
    except:
        logger.error("Failed to create email")
        await asyncio.sleep(1)
        return await create_email(client)


async def check_email(client: ClientSession, login: str, domain: str, count: int):
    try:
        response = await client.get('https://www.1secmail.com/api/v1/?action=getMessages&'
                                    f'login={login}&domain={domain}')
        email_id = (await response.json())[0]['id']
        return email_id
    except:
        while count < 30:
            count += 1
            await asyncio.sleep(1)
            return await check_email(client, login, domain, count)
        logger.error('Emails not found')
        raise Exception()


async def get_code(client: ClientSession, login: str, domain: str, email_id):
    try:
        response = await client.get('https://www.1secmail.com/api/v1/?action=readMessage&'
                                    f'login={login}&domain={domain}&id={email_id}')
        data = (await response.json())['body']
        code = findall(r"\d{6}", data)[2]
        return code
    except:
        logger.error('Failed to get code')
        raise Exception()


def create_wallet():
    account = w3.eth.account.create()
    return(str(account.address), str(account.privateKey.hex()))


async def send_email(client: ClientSession, email: str, address: str):
    response = await client.post('https://govendible.com/api/verify-email',
                                 json={
                                     "email": email,
                                     "address": address,
                                     "network": "polygon",
                                     "social": []
                                 }, headers={'token': ''})
    (await response.json())['token']


async def register(client: ClientSession, email: str, address: str, code: str):
    response = await client.post('https://govendible.com/api/rewards-register',
                                 json={
                                     "email": email,
                                     "address": address,
                                     "network": "polygon",
                                     "code": code,
                                     "referral": ref,
                                     "social": []
                                 }, headers={'token': email})
    return((await response.json())['coupon_code'])


async def worker():
    while True:
        try:
            async with aiohttp.ClientSession() as client:

                address, private_key = create_wallet()

                logger.info('Create email')
                email = await create_email(client)

                logger.info('Send email')
                await send_email(client, email, address.lower())

                logger.info('Check email')
                email_id = await check_email(client, email.split('@')[0], email.split('@')[1], 0)

                logger.info('Get code')
                code = await get_code(client, email.split('@')[0], email.split('@')[1], email_id)

                logger.info('Registration')
                unique_code = await register(client, email, address.lower(), code)

        except Exception:
            logger.error("Error\n")
        else:
            with open('registered.txt', 'a', encoding='utf-8') as file:
                file.write(f'{email}:{unique_code}:{address}:{private_key}\n')
            logger.success('Successfully\n')

        await asyncio.sleep(delay)


async def main():
    tasks = [asyncio.create_task(worker()) for _ in range(threads)]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    print("Bot Vendible @flamingoat\n")

    ref = input('Referral code: ')
    delay = int(input('Delay(sec): '))
    threads = int(input('Threads: '))

    asyncio.run(main())
