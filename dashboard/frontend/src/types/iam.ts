export interface IAMUser {
  id: number;
  username: string;
  email: string;
  name: string;
  role_id: number;
  role_name: string;
  active: boolean;
  created_at: string;
  last_login_at: string | null;
  rate_limit_override?: number | null;
  updated_at?: string;
}

export interface Role {
  id: number;
  name: string;
  description: string;
  mcp_access: string[];
  tool_restrictions: Record<string, any>;
  dashboard_access: string;
  rate_limit: number;
  cost_limit_daily: number;
  token_expiry: number;
  created_at?: string;
  updated_at?: string;
}

export interface Team {
  id: number;
  name: string;
  description: string;
  created_at: string;
  member_count?: number;
}
