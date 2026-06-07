#!/usr/bin/env node

import crypto from 'node:crypto';
import http from 'node:http';
import https from 'node:https';

const env = process.env;

function value(name, fallback = '') {
  return (env[name] || fallback).trim();
}

function boolValue(name) {
  return ['1', 'true', 'yes', 'on'].includes(value(name).toLowerCase());
}

function limitLines(text, maxLines) {
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (lines.length <= maxLines) {
    return lines.join('\n');
  }
  return `${lines.slice(0, maxLines).join('\n')}\n... and ${lines.length - maxLines} more`;
}

function markdownEscape(text) {
  return String(text || '').replace(/([*_`~])/g, '\\$1');
}

function buildCard() {
  const title = value('DOC_CHANGE_TITLE', 'BeeX Doc 仓库有更新');
  const repo = value('DOC_CHANGE_REPO', 'seahub-x-doc');
  const branch = value('DOC_CHANGE_BRANCH', 'main');
  const commit = value('DOC_CHANGE_COMMIT');
  const author = value('DOC_CHANGE_AUTHOR');
  const summary = limitLines(value('DOC_CHANGE_SUMMARY'), 12) || '- No commit summary';
  const files = limitLines(value('DOC_CHANGE_FILES'), 30) || '- No file list';
  const url = value('DOC_CHANGE_URL');
  const eventName = value('DOC_CHANGE_EVENT', 'push');

  const elements = [
    {
      tag: 'div',
      text: {
        tag: 'lark_md',
        content: [
          `**仓库**：${markdownEscape(repo)}`,
          `**分支**：${markdownEscape(branch)}`,
          commit ? `**提交**：${markdownEscape(commit)}` : '',
          author ? `**提交人**：${markdownEscape(author)}` : '',
          `**事件**：${markdownEscape(eventName)}`,
        ].filter(Boolean).join('\n'),
      },
    },
    {
      tag: 'hr',
    },
    {
      tag: 'div',
      text: {
        tag: 'lark_md',
        content: `**提交摘要**\n${markdownEscape(summary)}`,
      },
    },
    {
      tag: 'div',
      text: {
        tag: 'lark_md',
        content: `**变更文件**\n${markdownEscape(files)}`,
      },
    },
  ];

  if (url) {
    elements.push({
      tag: 'action',
      actions: [
        {
          tag: 'button',
          text: {
            tag: 'plain_text',
            content: '查看提交',
          },
          type: 'primary',
          url,
        },
      ],
    });
  }

  return {
    config: {
      wide_screen_mode: true,
    },
    header: {
      template: 'yellow',
      title: {
        tag: 'plain_text',
        content: title,
      },
    },
    elements,
  };
}

function requestJson(urlString, payload, headers = {}) {
  return new Promise((resolve, reject) => {
    const url = new URL(urlString);
    const body = JSON.stringify(payload);
    const client = url.protocol === 'http:' ? http : https;
    const request = client.request(
      {
        method: 'POST',
        hostname: url.hostname,
        port: url.port || undefined,
        path: `${url.pathname}${url.search}`,
        headers: {
          'Content-Type': 'application/json; charset=utf-8',
          'Content-Length': Buffer.byteLength(body),
          ...headers,
        },
      },
      (response) => {
        let responseBody = '';
        response.setEncoding('utf8');
        response.on('data', (chunk) => {
          responseBody += chunk;
        });
        response.on('end', () => {
          let parsed = {};
          try {
            parsed = responseBody ? JSON.parse(responseBody) : {};
          } catch {
            parsed = { raw: responseBody };
          }
          if (response.statusCode < 200 || response.statusCode >= 300) {
            reject(new Error(`HTTP ${response.statusCode}: ${responseBody}`));
            return;
          }
          resolve(parsed);
        });
      },
    );
    request.on('error', reject);
    request.write(body);
    request.end();
  });
}

async function getTenantAccessToken() {
  const appId = value('FEISHU_APP_ID');
  const appSecret = value('FEISHU_APP_SECRET');
  if (!appId || !appSecret) {
    throw new Error('Missing FEISHU_APP_ID or FEISHU_APP_SECRET.');
  }

  const baseUrl = value('FEISHU_OPEN_API_BASE', 'https://open.feishu.cn').replace(/\/$/, '');
  const response = await requestJson(`${baseUrl}/open-apis/auth/v3/tenant_access_token/internal`, {
    app_id: appId,
    app_secret: appSecret,
  });

  if (response.code !== 0 || !response.tenant_access_token) {
    throw new Error(`Failed to get Feishu tenant_access_token: ${JSON.stringify(response)}`);
  }
  return response.tenant_access_token;
}

async function sendByAppBot(card) {
  const receiveId = value('FEISHU_CHAT_ID') || value('FEISHU_RECEIVE_ID');
  const receiveIdType = value('FEISHU_RECEIVE_ID_TYPE', 'chat_id');
  if (!receiveId) {
    throw new Error('Missing FEISHU_CHAT_ID or FEISHU_RECEIVE_ID.');
  }

  const token = await getTenantAccessToken();
  const baseUrl = value('FEISHU_OPEN_API_BASE', 'https://open.feishu.cn').replace(/\/$/, '');
  const response = await requestJson(
    `${baseUrl}/open-apis/im/v1/messages?receive_id_type=${encodeURIComponent(receiveIdType)}`,
    {
      receive_id: receiveId,
      msg_type: 'interactive',
      content: JSON.stringify(card),
    },
    {
      Authorization: `Bearer ${token}`,
    },
  );

  if (response.code !== 0) {
    throw new Error(`Failed to send Feishu app bot message: ${JSON.stringify(response)}`);
  }
  return response;
}

function webhookSign(timestamp, secret) {
  const stringToSign = `${timestamp}\n${secret}`;
  return crypto.createHmac('sha256', secret).update(stringToSign).digest('base64');
}

async function sendByWebhook(card) {
  const webhookUrl = value('FEISHU_WEBHOOK_URL') || value('SEAHUB_FEISHU_WEBHOOK_URL');
  if (!webhookUrl) {
    throw new Error('Missing FEISHU_WEBHOOK_URL.');
  }

  const payload = {
    msg_type: 'interactive',
    card,
  };
  const secret = value('FEISHU_WEBHOOK_SECRET') || value('SEAHUB_FEISHU_WEBHOOK_SECRET');
  if (secret) {
    const timestamp = String(Math.floor(Date.now() / 1000));
    payload.timestamp = timestamp;
    payload.sign = webhookSign(timestamp, secret);
  }

  const response = await requestJson(webhookUrl, payload);
  if (response.code !== 0 && response.StatusCode !== 0) {
    throw new Error(`Failed to send Feishu webhook message: ${JSON.stringify(response)}`);
  }
  return response;
}

async function main() {
  const card = buildCard();
  if (boolValue('FEISHU_NOTIFY_DRY_RUN')) {
    console.log(JSON.stringify(card, null, 2));
    return;
  }

  const mode = value('FEISHU_NOTIFY_MODE', 'auto');
  const hasWebhook = Boolean(value('FEISHU_WEBHOOK_URL') || value('SEAHUB_FEISHU_WEBHOOK_URL'));
  const hasAppBot = Boolean((value('FEISHU_CHAT_ID') || value('FEISHU_RECEIVE_ID')) && value('FEISHU_APP_ID') && value('FEISHU_APP_SECRET'));

  if (mode === 'webhook' || (mode === 'auto' && hasWebhook)) {
    await sendByWebhook(card);
    console.log('Feishu webhook notification sent.');
    return;
  }

  if (mode === 'app' || (mode === 'auto' && hasAppBot)) {
    await sendByAppBot(card);
    console.log('Feishu app bot notification sent.');
    return;
  }

  const message = 'No Feishu notification target configured. Set FEISHU_CHAT_ID + FEISHU_APP_ID + FEISHU_APP_SECRET, or FEISHU_WEBHOOK_URL.';
  if (boolValue('FEISHU_NOTIFY_REQUIRED')) {
    throw new Error(message);
  }
  console.warn(message);
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
