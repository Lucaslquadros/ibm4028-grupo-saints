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

/** Um envio da planilha-modelo de fechamento: um ou vários meses, com os dois
 * lados e o movimento de estoque. O período vem no arquivo. */
export interface UploadFechamento {
  id: number;
  casa_id: number;
  nome_original: string;
  url: string;
  criado_em: string;
  periodos: string[];
  linhas_importadas: number;
  /** Meses do arquivo que já existiam e foram trocados por inteiro. */
  meses_substituidos: string[];
}

/** A casa de demonstração da planilha de fechamento (dados fictícios). */
export interface DemoFechamento {
  casa_nome: string;
  periodos: string[];
  periodos_historico: string[];
  periodo_ao_vivo: string;
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

/** Quanto o grupo puxou o ajuste do mês, em pontos do TOTAL.
 *
 * Não é o `ajuste_pp` de `LinhaFechamento`: lá o denominador é a venda do
 * próprio grupo, e por isso aquele número não soma ao total. Este soma.
 */
export interface ContribuicaoGrupo {
  grupo: string;
  ajuste: number;
  contribuicao_pp: number;
}

export interface SubgrupoComparado {
  grupo: string;
  subgrupo: string;
  custo_teorico: number;
  custo_real: number;
  ajuste: number;
  ajuste_pp: number | null;
}

/** Subgrupo que existe em um lado só: composição do custo, nunca desvio. */
export interface SubgrupoSemPar {
  grupo: string;
  subgrupo: string;
  lado: "teorico" | "real";
  custo: number;
}

/** Três situações, não duas: ajuste negativo não é economia. */
export type SituacaoAjuste = "acima" | "dentro" | "abaixo";

export interface Explicacao {
  situacao: SituacaoAjuste;
  /** Margem tratada como normal, em pontos. É premissa nossa — a tela exibe. */
  limiar_pp: number;
  resumo: string;
  /** No máximo 2. Vazia quando o ajuste está dentro da margem. */
  sugestoes: string[];
  contribuicoes: ContribuicaoGrupo[];
  grupos_sem_par: string[];
  subgrupos_comparados: SubgrupoComparado[];
  subgrupos_sem_par: SubgrupoSemPar[];
  limite_dado: string;
  /** false quando o lado real é só compras (sem estoque): aí a situação não é
   * diagnóstico do mês. Opcional: backend antigo não manda. */
  conclusivo?: boolean;
}

/** Em que base está o lado real.
 * - consumo: estoque inicial + compras − estoque final — o CMV real
 * - compras: só as compras do mês (DRE do Everest), falta o estoque
 * - declarada: planilha com uma coluna "custo"; o usuário declara que é o real */
export type BaseReal = "consumo" | "compras" | "declarada";

/** Teórico × real somados nos meses com os dois lados (janela de 12 meses). */
export interface Acumulado {
  periodo_inicio: string;
  periodo_fim: string;
  meses: number;
  periodos: string[];
  base_real: BaseReal;
  conclusivo: boolean;
  meses_minimos: number;
  ajuste_mensal_min_pp: number | null;
  ajuste_mensal_max_pp: number | null;
  total: LinhaFechamento;
  grupos: LinhaFechamento[];
}

export interface Fechamento {
  casa_id: number;
  casa_nome: string;
  periodo: string;
  tem_cardapio: boolean;
  tem_compras: boolean;
  total: LinhaFechamento;
  grupos: LinhaFechamento[];
  /** RF11. Opcional de propósito: entre o deploy do backend e o do front, a
   * resposta em produção pode não ter este campo — a tela não pode quebrar. */
  explicacao?: Explicacao | null;
  /** Opcionais pelo mesmo motivo de `explicacao`. */
  base_real?: BaseReal | null;
  acumulado?: Acumulado | null;
}

export interface PontoEvolucao {
  periodo: string;
  cmv_teorico_pct: number | null;
  cmv_real_pct: number | null;
  ajuste_pp: number | null;
  base_real?: BaseReal | null;
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

export type ClasseCardapio = "estrela" | "burro_de_carga" | "quebra_cabeca" | "cao";

/** Um item do cardápio no mês, no seu quadrante de popularidade × margem. */
export interface ItemEngenharia {
  nome: string;
  grupo: string;
  subgrupo: string | null;
  /** Categoria de cardápio em que o item foi comparado (subgrupo do ERP ou OUTROS). */
  categoria?: string | null;
  quantidade: number;
  venda_liquida: number;
  custo: number;
  preco_medio: number;
  custo_unitario: number;
  margem_unitaria: number;
  margem_total: number;
  cmv_pct: number;
  /** Nulo para item fora da matriz por volume (venda abaixo da venda mínima). */
  popularidade_pct: number | null;
  classe: ClasseCardapio | null;
  abaixo_do_custo: boolean;
}

export interface GrupoEngenharia {
  grupo: string;
  categoria?: string | null;
  itens: number;
  unidades: number;
  margem_total: number;
  margem_media_unitaria: number;
  limiar_popularidade_pct: number;
  estrela: number;
  burro_de_carga: number;
  quebra_cabeca: number;
  cao: number;
  fora_da_matriz?: number;
}

export interface EngenhariaCardapio extends Pagina<ItemEngenharia> {
  casa_id: number;
  casa_nome: string;
  periodo: string;
  grupos: GrupoEngenharia[];
  abaixo_do_custo: ItemEngenharia[];
  abaixo_do_custo_total?: number;
  abaixo_do_custo_prejuizo?: number;
  venda_minima?: number;
  metodo: string;
  aviso: string;
}

/** Margem por item: o mesmo item do cardápio no mês e no mês-base. */
export interface MargemItem {
  nome: string;
  grupo: string;
  subgrupo: string | null;
  quantidade: number;
  venda_liquida: number;
  custo: number;
  cmv_base_pct: number;
  cmv_atual_pct: number;
  variacao_pp: number;
  custo_unitario_base: number;
  custo_unitario_atual: number;
  variacao_custo_pct: number | null;
  preco_unitario_base: number;
  preco_unitario_atual: number;
  variacao_preco_pct: number | null;
  /** Quanto custou a mais no mês do que custaria com o CMV do mês-base. */
  custo_extra: number;
  serie: { periodo: string; cmv_pct: number | null }[];
}

export interface MargemItens extends Pagina<MargemItem> {
  casa_id: number;
  casa_nome: string;
  periodo: string;
  periodo_base: string;
  criterio_base: string;
  limiar_pp: number;
  venda_minima: number;
  itens_comparados: number;
  itens_que_pioraram: number;
  custo_extra_total: number;
  aviso: string;
}

export const api = {
  /** Link direto para a planilha-modelo. Não passa por `pedido`: a API
   * devolve um arquivo com Content-Disposition, não JSON. */
  urlModelo: (tipo: TipoUpload | "fechamento") => `${BASE_URL}/api/v1/modelos/${tipo}`,

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

  demoFechamento: () => pedido<DemoFechamento>("/api/v1/modelos/fechamento/demo"),

  /** Planilha preenchida da casa de demonstração, do mês pedido. */
  urlPlanilhaDemo: (periodo: string) =>
    `${BASE_URL}/api/v1/modelos/fechamento/demo/planilha?periodo=${periodo}`,

  /** Engenharia de cardápio por item da casa de demonstração, do mês pedido. */
  urlCardapioDemo: (periodo: string) =>
    `${BASE_URL}/api/v1/modelos/fechamento/demo/cardapio?periodo=${periodo}`,

  enviarPlanilhaFechamento: (dados: { casa_id: number; arquivo: File }) => {
    const form = new FormData();
    form.set("casa_id", String(dados.casa_id));
    form.set("arquivo", dados.arquivo);
    return pedido<UploadFechamento>("/api/v1/fechamentos", { method: "POST", body: form });
  },

  listarPlanilhasFechamento: (casaId: number) =>
    pedido<Pagina<UploadFechamento>>(`/api/v1/fechamentos?casa_id=${casaId}&limit=100`),

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

  margemItens: (casaId: number, periodo: string, base = "", limit = 20, offset = 0) => {
    const q = new URLSearchParams({
      casa_id: String(casaId),
      periodo,
      limit: String(limit),
      offset: String(offset),
    });
    if (base) q.set("base", base);
    return pedido<MargemItens>(`/api/v1/metricas/margem-itens?${q}`);
  },

  engenhariaCardapio: (
    casaId: number,
    periodo: string,
    grupo: string,
    categoria: string | null,
    limit = 200,
    offset = 0,
  ) => {
    const q = new URLSearchParams({
      casa_id: String(casaId),
      periodo,
      grupo,
      limit: String(limit),
      offset: String(offset),
    });
    if (categoria) q.set("categoria", categoria);
    return pedido<EngenhariaCardapio>(`/api/v1/metricas/engenharia-cardapio?${q}`);
  },

  /** Só o resumo (grupos e itens abaixo do custo): a página de itens vem vazia. */
  engenhariaResumo: (casaId: number, periodo: string) =>
    pedido<EngenhariaCardapio>(
      `/api/v1/metricas/engenharia-cardapio?casa_id=${casaId}&periodo=${periodo}&limit=1`,
    ),
};
