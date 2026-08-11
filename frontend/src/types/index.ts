// Core entities
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'manager' | 'user';
  tenantId: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  plan: string;
}

// Website Builder
export interface Page {
  id: string;
  tenant_id: string;
  title: string;
  slug: string;
  status: 'draft' | 'published';
  meta_title?: string;
  meta_description?: string;
  created_at: string;
  updated_at: string;
}

export interface PageComponent {
  id: string;
  page_id: string;
  type: ComponentType;
  order_index: number;
  props: Record<string, any>;
  styles: Record<string, any>;
}

export type ComponentType =
  | 'header'
  | 'text'
  | 'image'
  | 'button'
  | 'card'
  | 'table'
  | 'form'
  | 'chart'
  | 'hero'
  | 'divider'
  | 'spacer'
  | 'columns'
  | 'video'
  | 'testimonial';

export interface ComponentDefinition {
  type: ComponentType;
  label: string;
  icon: string;
  defaultProps: Record<string, any>;
  category: 'layout' | 'content' | 'media' | 'data' | 'interactive';
}

// HR
export interface Employee {
  id: string;
  employee_number: string;
  name: string;
  email: string;
  department: string;
  position: string;
  hire_date: string;
  salary: number;
  status: 'active' | 'inactive';
}

// Finance
export interface Budget {
  id: string;
  name: string;
  department: string;
  amount: number;
  spent: number;
  period: string;
  fiscal_year: number;
  status: string;
}

export interface Expense {
  id: string;
  budget_id: string;
  category: string;
  amount: number;
  description: string;
  date: string;
  status: 'pending' | 'approved' | 'rejected';
}

// CRM
export interface Customer {
  id: string;
  name: string;
  email: string;
  phone: string;
  company: string;
  industry: string;
  status: 'lead' | 'prospect' | 'customer' | 'churned';
}

export interface Deal {
  id: string;
  customer_id: string;
  customer_name?: string;
  title: string;
  value: number;
  stage: 'prospecting' | 'qualification' | 'proposal' | 'negotiation' | 'closed_won' | 'closed_lost';
  probability: number;
  close_date: string;
}

// Inventory
export interface InventoryItem {
  id: string;
  sku: string;
  name: string;
  category: string;
  quantity: number;
  unit_cost: number;
  selling_price: number;
  reorder_level: number;
  location: string;
  supplier: string;
}

// Tasks
export interface Task {
  id: string;
  title: string;
  description: string;
  assignee_id: string;
  assignee_name?: string;
  status: 'todo' | 'in_progress' | 'review' | 'done';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  due_date: string;
  module: string;
}

// Plugin
export interface Plugin {
  id: string;
  name: string;
  version: string;
  is_active: number;
  config: string;
}

// Auth
export interface AuthState {
  token: string | null;
  user: User | null;
  tenant: Tenant | null;
}
