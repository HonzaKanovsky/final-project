const express = require('express');
const https = require('https');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');

const options = {
  key: fs.readFileSync('key.pem'),
  cert: fs.readFileSync('cert.pem'),
};

const app = express();
const HTTPS_PORT = 8443;

const server = https.createServer(options, app);
const wss = new WebSocket.Server({ server });

app.use(express.static(path.join(__dirname, 'public')));

const clients = {};
const NUM_SLOTS = 6;

wss.on('connection', (ws, req) => {
  const clientId = generateId();
  const url = new URL(req.url, `https://${req.headers.host}`);
  const clientType = url.searchParams.get('type');

  if (clientType === 'camera') {
    const slot = assignSlot();
    if (slot === -1) {
      ws.close(1000, 'All slots full');
      return;
    }

    // Get the remote public IP
    const remoteAddress = req.socket.remoteAddress;

    clients[clientId] = { ws, type: 'camera', slot };
    console.log(`Camera connected in slot ${slot} from IP ${remoteAddress}`);

    // Send IP to all viewers
    broadcastToViewersRaw(JSON.stringify({
      type: 'ip',
      slot,
      ip: remoteAddress.replace('::ffff:', '')
    }));

    ws.on('message', (data) => {
      try {
        // Check if the message is JSON (IP update) or binary (frame data)
        if (data instanceof Buffer) {
          // It's a frame, send it directly
          console.log(`Received frame data of length ${data.length} from slot ${slot}`);
          if (data.length > 100) { // Only process frames larger than 100 bytes
            broadcastFrame(data, slot);
          } else {
            console.log('Frame too small, skipping');
          }
        } else {
          // It's a JSON message (like IP update)
          const message = JSON.parse(data);
          if (message.type === 'ip') {
            broadcastToViewersRaw(JSON.stringify({
              type: 'ip',
              slot,
              ip: message.ip
            }));
          }
        }
      } catch (error) {
        console.error('Error processing message:', error);
      }
    });

  } else if (clientType === 'viewer') {
    clients[clientId] = { ws, type: 'viewer' };
    console.log('Viewer connected');
  }

  ws.on('close', () => {
    const client = clients[clientId];
    if (!client) return;

    console.log(`${client.type} disconnected`);

    // If it's a camera, inform viewers to reset the slot
    if (client.type === 'camera') {
      const slot = client.slot;

      const message = JSON.stringify({
        type: 'ip',
        slot,
        ip: 'Disconnected'
      });

      Object.values(clients).forEach(c => {
        if (c.type === 'viewer' && c.ws.readyState === WebSocket.OPEN) {
          c.ws.send(message);
        }
      });
    }

    delete clients[clientId];
  });
});

function assignSlot() {
  const usedSlots = new Set();
  Object.values(clients).forEach(client => {
    if (client.type === 'camera') usedSlots.add(client.slot);
  });

  for (let i = 0; i < NUM_SLOTS; i++) {
    if (!usedSlots.has(i)) return i;
  }
  return -1;
}

function broadcastFrame(frameData, slot) {
  try {
    // Convert the binary data to base64
    const base64Data = frameData.toString('base64');
    
    // Create the message with proper formatting
  const message = JSON.stringify({
    type: 'frame',
    slot,
      data: base64Data
  });

    // Send to all viewers
  Object.values(clients).forEach(client => {
    if (client.type === 'viewer' && client.ws.readyState === WebSocket.OPEN) {
      client.ws.send(message);
    }
  });
  } catch (error) {
    console.error('Error broadcasting frame:', error);
  }
}

function broadcastToViewersRaw(rawMessage) {
  Object.values(clients).forEach(client => {
    if (client.type === 'viewer' && client.ws.readyState === WebSocket.OPEN) {
      client.ws.send(rawMessage);
    }
  });
}

function generateId() {
  return Math.random().toString(36).substr(2, 9);
}

server.listen(HTTPS_PORT, '0.0.0.0', () => {
  console.log(`HTTPS and WSS server running at https://0.0.0.0:${HTTPS_PORT}`);
});
