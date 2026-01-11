require('dotenv').config();
const { Client, GatewayIntentBits, Collection, REST, Routes } = require('discord.js');
const mongoose = require('mongoose');
const fs = require('fs');
const path = require('path');

// Initialize Client
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.GuildVoiceStates
  ]
});

client.commands = new Collection();

// Load Commands
const commandsPath = path.join(__dirname, 'commands');
const commandFiles = fs.readdirSync(commandsPath).filter(file => file.endsWith('.js'));

const commands = [];

for (const file of commandFiles) {
  const filePath = path.join(commandsPath, file);
  const command = require(filePath);
  if ('data' in command && 'execute' in command) {
    client.commands.set(command.data.name, command);
    commands.push(command.data.toJSON());
  } else {
    console.log(`[WARNING] The command at ${filePath} is missing a required "data" or "execute" property.`);
  }
}

// Database Connection
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/broski-bot')
  .then(() => console.log('✅ Connected to MongoDB'))
  .catch(err => console.warn('❌ MongoDB Connection Error:', err));

// Event Handling
client.once('ready', async () => {
  console.log(`🤖 BROski Bot Online! Logged in as ${client.user.tag}`);
  
  // Register Slash Commands
  const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
  const clientId = client.user.id;

  try {
    console.log('🔄 Refreshing application (/) commands...');
    
    // Strategy: If GUILD_ID is present, register there.
    // If NOT present, register in ALL guilds the bot is currently in (Best for testing)
    const guildId = process.env.GUILD_ID;

    if (guildId) {
        console.log(`🎯 Registering commands for Guild: ${guildId}`);
        await rest.put(
            Routes.applicationGuildCommands(clientId, guildId),
            { body: commands },
        );
    } else {
        console.log('🌐 No GUILD_ID in .env. Registering commands for ALL joined guilds (Dev Mode)...');
        const guilds = client.guilds.cache.map(g => g.id);
        if (guilds.length === 0) {
            console.log('⚠️ Bot is not in any guilds yet. Invite it using the URL generated in Developer Portal!');
        }
        for (const gId of guilds) {
            console.log(`   - Registering for guild: ${gId}`);
            await rest.put(
                Routes.applicationGuildCommands(clientId, gId),
                { body: commands },
            );
        }
    }
    console.log('✅ Successfully reloaded application (/) commands.');
  } catch (error) {
    console.error('❌ Command Registration Failed:', error);
  }
});

client.on('interactionCreate', async interaction => {
  if (!interaction.isChatInputCommand()) return;

  const command = client.commands.get(interaction.commandName);

  if (!command) return;

  try {
    await command.execute(interaction);
  } catch (error) {
    console.error(error);
    if (interaction.replied || interaction.deferred) {
      await interaction.followUp({ content: 'There was an error while executing this command!', ephemeral: true });
    } else {
      await interaction.reply({ content: 'There was an error while executing this command!', ephemeral: true });
    }
  }
});

// Login
if (process.env.DISCORD_TOKEN) {
    client.login(process.env.DISCORD_TOKEN);
} else {
    console.log("⚠️ DISCORD_TOKEN not set. Bot will not login.");
}
