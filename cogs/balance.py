import discord, json, requests, pymysql.cursors
from discord.ext import commands
from utils import rpc_module, mysql_module

#result_set = database response with parameters from query
#db_bal = nomenclature for result_set["balance"]
#author = author from message context, identical to user in database
#wallet_bal = nomenclature for wallet reponse

rpc = rpc_module.Rpc()
Mysql = mysql_module.Mysql()


class Balance:

    def __init__(self, bot):
        self.bot = bot

    async def do_embed(self, author, db_bal):
        # Simple embed function for displaying username and balance
        embed = discord.Embed(colour=discord.Colour.red())
        embed.add_field(name="User", value=author)
        embed.add_field(name="Balance (NET)", value="%.8f" % round(float(db_bal),8))
        embed.set_footer(text="Sponsored by altcointrain.com - Choo!!! Choo!!!")

        try:
            await self.bot.say(embed=embed)
        except discord.HTTPException:
            await self.bot.say("I need the `Embed links` permission to send this")

    async def parse_part_bal(self,result_set,author):
        # If user has a lasttxid value in the db, then stop parsing
        # trans-list at a specific ["txid"] and submit
        # changes to update_db
        params = author
        count = 1000
        get_transactions = rpc.listtransactions(params,count)
        i = len(get_transactions)-1

        new_balance = float(result_set["balance"])
        lasttxid = get_transactions[i]["txid"]
        if lasttxid == result_set["lasttxid"]:
            db_bal = result_set["balance"]
            await self.do_embed(author, db_bal)
        else:
            for tx in reversed(get_transactions):
                new_balance += float(tx["amount"])
                if tx["txid"] == result_set["lasttxid"]:
                    break
            db_bal = new_balance
            Mysql.update_db(author, db_bal, lasttxid)
            await self.do_embed(author, db_bal)

    async def parse_whole_bal(self,result_set,author):
        # If a user does not have a lasttxid in the db, the parse
        # the entire trans-list for that user. Submit changes to
        # update_db
        params = author
        user = params
        count = 1000
        get_transactions = rpc.listtransactions(params,count)
        i = len(get_transactions)-1

        if len(get_transactions) == 0:
            print("0 transactions found for "+author+", balance must be 0")
            db_bal = 0
            await self.do_embed(author, db_bal)
        else:
            new_balance = 0
            lasttxid = get_transactions[i]["txid"]
            firsttxid = get_transactions[0]["txid"]
            while i <= len(get_transactions)-1:
                if get_transactions[i]["txid"] != firsttxid:
                    new_balance += float(get_transactions[i]["amount"])
                    i -= 1
                else:
                    new_balance += float(get_transactions[i]["amount"])
                    break
            db_bal = new_balance
            self.update_db(author, db_bal, lasttxid)
            await self.do_embed(author, db_bal)
            #Now update db with new balance

    @commands.command(pass_context=True)
    async def balance(self, ctx):
        # Set important variables
        author = str(ctx.message.author)

        # Check if user exists in db
        result_set = Mysql.check_for_user(author)


        # Execute and return SQL Query
        result_set = Mysql.get_user(author)

        if result_set["lasttxid"] == "0":
            await self.parse_whole_bal(result_set,author)
        else:
            await self.parse_part_bal(result_set,author)


def setup(bot):
    bot.add_cog(Balance(bot))
