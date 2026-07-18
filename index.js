const { Client, Intents } = require('discord.js-selfbot-v13');

const TOKEN = process.env.TOKEN;
if (!TOKEN) {
  console.error('❌ TOKEN environment variable is missing.');
  process.exit(1);
}

const client = new Client({
  intents: [Intents.FLAGS.GUILDS, Intents.FLAGS.GUILD_MESSAGES, Intents.FLAGS.DIRECT_MESSAGES],
});

client.on('ready', () => {
  console.log(`✅ Logged in as ${client.user.tag}`);
});

client.on('messageCreate', async (message) => {
  // Ignore own messages
  if (message.author.id === client.user.id) return;

  // Reply with "hi" if the bot is mentioned
  if (message.mentions.has(client.user.id)) {
    await message.reply('hi');
  }
});

client.login(TOKEN);
