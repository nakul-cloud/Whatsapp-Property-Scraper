export interface PropertyLead {
  property_id: string;
  property_type: string;
  owner_name: string;
  owner_contact: string;
  area: string;
  address: string;
  size: string;
  rent_or_sell_price: string;
  deposit: string;
  date_stamp: string;
}

export interface ProcessResponse {
  rows: PropertyLead[];
  meta: {
    message_count: number;
    parsed_count: number;
    ai_used: boolean;
    ai_candidates: number;
    failures: string[];
    audit_failed: FailedMessage[];
    debug: string[];
    areas_loaded: number;
  };
}

export interface FailedMessage {
  idx: number;
  date_stamp: string;
  missing_fields: string;
  raw_message: string;
}

export interface KPIData {
  totalLeads: number;
  uniqueContacts: number;
  avgPrice: number;
  dataQuality: number;
}

export interface GroqConfig {
  enabled: boolean;
  apiKey: string;
  model: string;
}

export interface ChartDataPoint {
  name: string;
  value: number;
  [key: string]: any;
}
