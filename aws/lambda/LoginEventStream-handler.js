// LoginEventStream-handler.js
const { SecretsManagerClient, GetSecretValueCommand } = require('@aws-sdk/client-secrets-manager');
const jwt = require('jsonwebtoken');
const { StreamingClient, Topic } = require('salesforce-pubsub-client');

exports.handler = async (event) => {
  const secretsClient = new SecretsManagerClient({});
  const secret = await secretsClient.send(new GetSecretValueCommand({ SecretId: 'salesforce/jwt-auth' }));
  const { clientId, username, loginUrl, privateKey } = JSON.parse(secret.SecretString);

  const audience = loginUrl;
  const token = jwt.sign(
    {
      iss: clientId,
      sub: username,
      aud: audience,
      exp: Math.floor(Date.now() / 1000) + 300
    },
    privateKey,
    { algorithm: 'RS256' }
  );

  const tokenResponse = await fetch(`${loginUrl}/services/oauth2/token`, {
    method: 'POST',
    body: new URLSearchParams({
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion: token
    }),
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  }).then(res => res.json());

  if (!tokenResponse.access_token) {
    throw new Error(`Auth failed: ${JSON.stringify(tokenResponse)}`);
  }

  const client = new StreamingClient({
    auth: {
      accessToken: tokenResponse.access_token,
      instanceUrl: tokenResponse.instance_url
    }
  });

  const topic = new Topic('/event/LoginEventStream');
  client.subscribe(topic, async (msg) => {
    console.log('Platform Event received:', JSON.stringify(msg));
    // Process or forward to another service (e.g., S3, DynamoDB, OpenSearch)
  });

  await client.connect();

  // Keep the connection open for 30 seconds (simulate a warm Lambda)
  await new Promise(resolve => setTimeout(resolve, 30000));
};
