const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function pedido<T>(caminho: string, opcoes?: RequestInit): Promise<T> {
  const resposta = await fetch(`${BASE_URL}${caminho}`, opcoes);
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => null);
    throw new ApiError(resposta.status, corpo?.detail ?? `Erro ${resposta.status}`);
  }
  if (resposta.status === 204) return undefined as T;
  return resposta.json() as Promise<T>;
}

export interface Casa {
  id: number;
  nome: string;
  marca: string;
  cidade: string;
  ativa: boolean;
  criado_em: string;
  atualizado_em: string;
}

export interface Pagina<T> {
  total: number;
  limit: number;
  offset: number;
  items: T[];
}

export type TipoUpload = "cardapio" | "compras";

export interface UploadCusto {
  id: number;
  casa_id: number;
  periodo: string;
  tipo: TipoUpload;
  nome_original: string;
  url: string;
  criado_em: string;
  linhas_importadas: number;
  substituiu_anterior: boolean;
}

export interface LinhaFechamento {
  grupo: string;
  venda_liquida: number | null;
  custo_teorico: number | null;
  custo_real: number | null;
  cmv_teorico_pct: number | null;
  cmv_real_pct: number | null;
  ajuste: number | null;
  ajuste_pp: number | null;
}

export interface Fechamento {
  casa_id: number;
  casa_nome: string;
  periodo: string;
  tem_cardapio: boolean;
  tem_compras: boolean;
  total: LinhaFechamento;
  grupos: LinhaFechamento[];
}

export interface PontoEvolucao {
  periodo: string;
  cmv_teorico_pct: number | null;
  cmv_real_pct: number | null;
  ajuste_pp: number | null;
}

export interface ItemCardapio {
  nome: string;
  grupo: string;
  subgrupo: string | null;
  quantidade: number | null;
  venda_liquida: number | null;
  custo: number;
  cmv_pct: number | null;
}

export const api = {
  listarCasas: (params: { ativa?: boolean; busca?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.ativa !== undefined) q.set("ativa", String(params.ativa));
    if (params.busca) q.set("busca", params.busca);
    q.set("limit", "100");
    return pedido<Pagina<Casa>>(`/api/v1/casas?${q}`);
  },

  criarCasa: (dados: { nome: string; marca: string; cidade: string; ativa: boolean }) =>
    pedido<Casa>("/api/v1/casas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dados),
    }),

  enviarUpload: (dados: {
    casa_id: number;
    periodo: string;
    tipo: TipoUpload;
    arquivo: File;
  }) => {
    const form = new FormData();
    form.set("casa_id", String(dados.casa_id));
    form.set("periodo", dados.periodo);
    form.set("tipo", dados.tipo);
    form.set("arquivo", dados.arquivo);
    return pedido<UploadCusto>("/api/v1/uploads-custo", { method: "POST", body: form });
  },

  listarUploads: (casaId: number) =>
    pedido<Pagina<UploadCusto>>(`/api/v1/uploads-custo?casa_id=${casaId}&limit=200`),

  fechamento: (casaId: number, periodo: string) =>
    pedido<Fechamento>(`/api/v1/metricas/fechamento?casa_id=${casaId}&periodo=${periodo}`),

  evolucao: (casaId: number, limit = 24) =>
    pedido<PontoEvolucao[]>(`/api/v1/metricas/evolucao?casa_id=${casaId}&limit=${limit}`),

  topItens: (casaId: number, periodo: string, ordem: "custo" | "cmv" = "custo") =>
    pedido<ItemCardapio[]>(
      `/api/v1/metricas/top-itens?casa_id=${casaId}&periodo=${periodo}&ordem=${ordem}`,
    ),
};
