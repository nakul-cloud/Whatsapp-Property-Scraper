import { ProcessResponse } from '../types';
import { generateMockResponse } from './mockData';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA === 'true';

export async function processMessages(
  messages: string,
  groqConfig?: { apiKey: string; model: string },
  customAreasPath?: string
): Promise<ProcessResponse> {
  // Use mock data if enabled or API is unavailable
  if (USE_MOCK_DATA) {
    await new Promise((resolve) => setTimeout(resolve, 1500)); // Simulate API delay
    const messageCount = messages.split(/\[\d{2}\/\d{2}\/\d{4}/).length - 1;
    return generateMockResponse(Math.max(messageCount, 1));
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        raw_text: messages,
        enable_ai_fallback: !!groqConfig,
        groq_api_key: groqConfig?.apiKey,
        groq_model: groqConfig?.model,
        area_path: customAreasPath,
      }),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    // Fallback to mock data if API is unavailable
    console.warn('API unavailable, using mock data:', error);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    const messageCount = messages.split(/\[\d{2}\/\d{2}\/\d{4}/).length - 1;
    return generateMockResponse(Math.max(messageCount, 1));
  }
}

export async function exportCSV(data: any[]): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/export_csv`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ rows: data }),
  });

  if (!response.ok) {
    throw new Error(`Export Error: ${response.statusText}`);
  }

  return response.blob();
}
