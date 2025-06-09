import os
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import logging
from difference_game_generator import DifferenceGameGenerator

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
#test
class GameBot:
    def __init__(self, token):
        self.token = token
        self.game_generator = DifferenceGameGenerator()
        self.users = {}  # In-memory user storage for local testing
        self.active_games = {}  # Store active games
        self.admin_id = None  # Set this to your Telegram user ID
        
    def load_user_data(self, user_id):
        """Load or create user data"""
        if user_id not in self.users:
            self.users[user_id] = {
                'user_id': user_id,
                'role': 'player',  # player, gamer, admin
                'coins': 0,
                'games_played': 0,
                'games_won': 0,
                'current_level': 50,
                'join_date': datetime.now().isoformat(),
                'total_deposited': 0,
                'total_withdrawn': 0
            }
        return self.users[user_id]
    
    def save_user_data(self, user_id, data):
        """Save user data"""
        self.users[user_id] = data
        # In production, this would save to database
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command - Welcome new users"""
        user = update.effective_user
        user_data = self.load_user_data(user.id)
        
        welcome_message = f"""
🎮 **Welcome to Find the Difference Arena!** 🎮

Hey {user.first_name}! Ready for the ultimate visual challenge?

💰 **Your Stats:**
• Coins: {user_data['coins']}
• Games Played: {user_data['games_played']}
• Win Rate: {(user_data['games_won']/max(1,user_data['games_played'])*100):.1f}%
• Current Level: {user_data['current_level']}%

🎯 **How it works:**
• Deposit TON → Get Coins (chat with admin)
• Play games with joining fees
• Find 5 differences to win
• Higher difficulty = Higher rewards!

**Commands:**
/play - Start a new game
/profile - View your profile
/leaderboard - Top players
/deposit - Request coin deposit
/withdraw - Request coin withdrawal

Ready to challenge your eyes? 👀
        """
        
        keyboard = [
            [InlineKeyboardButton("🎮 Play Game", callback_data="play_game")],
            [InlineKeyboardButton("👤 Profile", callback_data="profile"),
             InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
            [InlineKeyboardButton("💰 Deposit", callback_data="deposit"),
             InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user profile"""
        user_data = self.load_user_data(update.effective_user.id)
        
        win_rate = (user_data['games_won']/max(1,user_data['games_played'])*100)
        
        profile_text = f"""
👤 **Your Profile**

💰 **Wallet:**
• Current Coins: {user_data['coins']}
• Total Deposited: {user_data['total_deposited']} TON
• Total Withdrawn: {user_data['total_withdrawn']} TON

🎮 **Gaming Stats:**
• Games Played: {user_data['games_played']}
• Games Won: {user_data['games_won']}
• Win Rate: {win_rate:.1f}%
• Current Difficulty: {user_data['current_level']}%

📅 **Account:**
• Role: {user_data['role'].title()}
• Joined: {user_data['join_date'][:10]}

🎯 **Next Level:** {min(90, user_data['current_level'] + 10)}% difficulty
        """
        
        keyboard = [
            [InlineKeyboardButton("🎮 Play Game", callback_data="play_game")],
            [InlineKeyboardButton("📊 Change Difficulty", callback_data="change_difficulty")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def play_game_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle play game button"""
        query = update.callback_query
        await query.answer()
        
        user_data = self.load_user_data(query.from_user.id)
        
        # Check if user has enough coins
        join_fee = self.calculate_join_fee(user_data['current_level'])
        
        if user_data['coins'] < join_fee:
            await query.edit_message_text(
                f"❌ **Insufficient Coins!**\n\n"
                f"You need {join_fee} coins to play at {user_data['current_level']}% difficulty.\n"
                f"Your balance: {user_data['coins']} coins\n\n"
                f"💰 Deposit more coins to continue playing!",
                parse_mode='Markdown'
            )
            return
        
        # Deduct join fee
        user_data['coins'] -= join_fee
        self.save_user_data(query.from_user.id, user_data)
        
        # Generate game
        await query.edit_message_text("🎮 **Generating your game...**\n\nPlease wait while we create a unique challenge for you! 🎯")
        
        try:
            game = self.game_generator.generate_game(
                difficulty_level=user_data['current_level'],
                num_differences=5
            )
            
            # Save game
            game_files = self.game_generator.save_game(game)
            game_id = game_files['game_id']
            
            # Store active game
            self.active_games[query.from_user.id] = {
                'game_id': game_id,
                'game_data': game['game_data'],
                'join_fee': join_fee,
                'start_time': datetime.now(),
                'attempts': 0,
                'found_differences': []
            }
            
            # Send game images
            with open(game_files['original_path'], 'rb') as f1, open(game_files['modified_path'], 'rb') as f2:
                
                game_text = f"""
🎯 **Find the Difference Challenge!**

💰 **Stakes:** {join_fee} coins
🎚️ **Difficulty:** {user_data['current_level']}%
🔍 **Find:** 5 differences
⏰ **Time:** Unlimited
💎 **Reward:** {self.calculate_reward(user_data['current_level'], join_fee)} coins

**Instructions:**
1. Compare both images carefully
2. Tap the differences you find
3. Find all 5 to win!

Good luck! 🍀
                """
                
                keyboard = [
                    [InlineKeyboardButton("📍 Mark Difference", callback_data=f"mark_diff_{game_id}")],
                    [InlineKeyboardButton("🚫 Give Up", callback_data=f"give_up_{game_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=f1,
                    caption="🖼️ **Original Image**"
                )
                
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=f2,
                    caption=game_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error generating game: {e}")
            # Refund join fee
            user_data['coins'] += join_fee
            self.save_user_data(query.from_user.id, user_data)
            
            await query.edit_message_text(
                "❌ **Game Generation Failed**\n\n"
                "Sorry, there was an error creating your game. Your coins have been refunded.\n\n"
                "Please try again in a moment!"
            )
    
    async def difficulty_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle difficulty selection"""
        query = update.callback_query
        await query.answer()
        
        difficulties = [50, 60, 70, 80, 90]
        user_data = self.load_user_data(query.from_user.id)
        
        keyboard = []
        for diff in difficulties:
            join_fee = self.calculate_join_fee(diff)
            reward = self.calculate_reward(diff, join_fee)
            
            status = "✅" if diff == user_data['current_level'] else "⚪"
            button_text = f"{status} {diff}% | Fee: {join_fee} | Win: {reward}"
            
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"set_diff_{diff}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Profile", callback_data="profile")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎚️ **Select Difficulty Level**\n\n"
            "Higher difficulty = Higher rewards but lower win chances!\n\n"
            "Current level highlighted with ✅",
            reply_markup=reply_markup
        )
    
    async def set_difficulty_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set user difficulty level"""
        query = update.callback_query
        await query.answer()
        
        difficulty = int(query.data.split('_')[2])
        user_data = self.load_user_data(query.from_user.id)
        user_data['current_level'] = difficulty
        self.save_user_data(query.from_user.id, user_data)
        
        await query.edit_message_text(
            f"✅ **Difficulty Updated!**\n\n"
            f"New level: {difficulty}%\n"
            f"Join fee: {self.calculate_join_fee(difficulty)} coins\n"
            f"Potential reward: {self.calculate_reward(difficulty, self.calculate_join_fee(difficulty))} coins\n\n"
            f"Ready to play at the new difficulty?"
        )
    
    async def deposit_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle deposit request"""
        query = update.callback_query
        await query.answer()
        
        deposit_text = f"""
💰 **Deposit TON for Coins**

**How it works:**
1. Send TON to admin wallet
2. Send transaction proof here
3. Admin manually credits your coins
4. Exchange rate: 1 TON = 100 coins

**Admin Contact:** @your_admin_username

**Your Info:**
• User ID: `{query.from_user.id}`
• Username: @{query.from_user.username or 'None'}
• Current Balance: {self.load_user_data(query.from_user.id)['coins']} coins

**Instructions:**
Send a message with your transaction details!
        """
        
        await query.edit_message_text(deposit_text, parse_mode='Markdown')


# Add this command for testing
    async def testcoins_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
       user_data = self.load_user_data(update.effective_user.id)
       user_data['coins'] += 1000
       self.save_user_data(update.effective_user.id, user_data)
       await update.message.reply_text("💰 Added 1000 test coins!")


    async def withdraw_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle withdrawal request"""
        query = update.callback_query
        await query.answer()
        
        user_data = self.load_user_data(query.from_user.id)
        min_withdrawal = 500  # Minimum coins for withdrawal
        
        if user_data['coins'] < min_withdrawal:
            await query.edit_message_text(
                f"❌ **Insufficient Balance**\n\n"
                f"Minimum withdrawal: {min_withdrawal} coins\n"
                f"Your balance: {user_data['coins']} coins\n\n"
                f"Keep playing to earn more coins! 🎮"
            )
            return
        
        withdraw_text = f"""
💸 **Withdraw Coins to TON**

**Your Balance:** {user_data['coins']} coins
**Exchange Rate:** 100 coins = 1 TON
**Available:** {user_data['coins']//100} TON

**How it works:**
1. Contact admin with withdrawal request
2. Provide your TON wallet address
3. Admin processes manually
4. Coins deducted after confirmation

**Admin Contact:** @your_admin_username

**Withdrawal Request Format:**
```
WITHDRAW REQUEST
User ID: {query.from_user.id}
Amount: [X] coins
TON Address: [your_address]
```

Copy and send to admin! 📋
        """
        
        await query.edit_message_text(withdraw_text, parse_mode='Markdown')
    
    def calculate_join_fee(self, difficulty):
        """Calculate join fee based on difficulty"""
        base_fee = 10
        return base_fee + (difficulty - 50) // 10 * 5
    
    def calculate_reward(self, difficulty, join_fee):
        """Calculate reward based on difficulty and join fee"""
        multiplier = 1.5 + (difficulty - 50) / 100
        return int(join_fee * multiplier)
    
    async def callback_router(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route callback queries to appropriate handlers"""
        query = update.callback_query
        data = query.data
        
        if data == "play_game":
            await self.play_game_callback(update, context)
        elif data == "profile":
            await self.profile_command(update, context)
        elif data == "change_difficulty":
            await self.difficulty_callback(update, context)
        elif data.startswith("set_diff_"):
            await self.set_difficulty_callback(update, context)
        elif data == "deposit":
            await self.deposit_callback(update, context)
        elif data == "withdraw":
            await self.withdraw_callback(update, context)
        elif data == "leaderboard":
            await self.leaderboard_callback(update, context)
    
    async def leaderboard_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show leaderboard"""
        query = update.callback_query
        await query.answer()
        
        # Sort users by coins
        sorted_users = sorted(self.users.values(), key=lambda x: x['coins'], reverse=True)[:10]
        
        leaderboard_text = "🏆 **Top Players**\n\n"
        
        for i, user in enumerate(sorted_users):
            emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
            win_rate = (user['games_won']/max(1,user['games_played'])*100)
            leaderboard_text += f"{emoji} {user['coins']} coins | {win_rate:.1f}% win rate\n"
        
        if not sorted_users:
            leaderboard_text += "No players yet! Be the first! 🎮"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(leaderboard_text, reply_markup=reply_markup, parse_mode='Markdown')

def main():
    """Main function to run the bot"""
    # Get bot token from environment variable
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not TOKEN:
        print("❌ Please set TELEGRAM_BOT_TOKEN environment variable")
        print("1. Create a bot with @BotFather on Telegram")
        print("2. Get your bot token")
        print("3. Export TELEGRAM_BOT_TOKEN='your_token_here'")
        return
    
    # Create bot instance
    bot = GameBot(TOKEN)
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    # Add this line in main() with other handlers:
    application.add_handler(CommandHandler("testcoins", bot.testcoins_command))
    
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("profile", bot.profile_command))
    application.add_handler(CallbackQueryHandler(bot.callback_router))
    
    # Start bot
    print("🤖 Bot starting...")
    print("Send /start to your bot on Telegram to test!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
