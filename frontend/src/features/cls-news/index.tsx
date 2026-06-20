import { useState, useEffect, useRef } from 'react'
import {
  Newspaper,
  RefreshCw,
  Search,
  Clock,
  Flame,
  Zap,
  TrendingDown,
  Brain,
  Send,
  Loader2,
  ExternalLink,
  Globe,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { ThemeSwitch } from '@/components/theme-switch'
import { ProfileDropdown } from '@/components/profile-dropdown'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Helper to format Date to YYYY-MM-DD HH:mm:ss
function formatDateTime(date: Date): string {
  const yyyy = date.getFullYear()
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const min = String(date.getMinutes()).padStart(2, '0')
  const ss = String(date.getSeconds()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd} ${hh}:${min}:${ss}`
}

interface NewsItem {
  unique_id: string
  id: string
  source: string
  title: string
  content: string
  pub_date: string
  is_red: boolean
  url: string
  importance_score: number
  asset_category: string
  process_status: string
}

export function ClsNews() {
  const [news, setNews] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  
  // Filters
  const [timeRange, setTimeRange] = useState<string>('12h')
  const [customStart, setCustomStart] = useState('')
  const [customEnd, setCustomEnd] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL')

  // AI State
  const [aiLoading, setAiLoading] = useState(false)
  const [aiResult, setAiResult] = useState<string>('')
  const [customQuery, setCustomQuery] = useState('')
  const [lastSyncTime, setLastSyncTime] = useState<string>('')

  const backendUrl = 'http://127.0.0.1:8000'
  const autoSyncIntervalRef = useRef<any>(null)

  // Compute start/end time strings
  const getTimeBounds = () => {
    const end = new Date()
    let start = new Date()

    switch (timeRange) {
      case '4h':
        start = new Date(end.getTime() - 4 * 60 * 60 * 1000)
        break
      case '12h':
        start = new Date(end.getTime() - 12 * 60 * 60 * 1000)
        break
      case '24h':
        start = new Date(end.getTime() - 24 * 60 * 60 * 1000)
        break
      case '3d':
        start = new Date(end.getTime() - 3 * 24 * 60 * 60 * 1000)
        break
      case 'custom':
        return {
          startStr: customStart ? customStart.replace('T', ' ') + ':00' : '',
          endStr: customEnd ? customEnd.replace('T', ' ') + ':00' : '',
        }
    }
    return {
      startStr: formatDateTime(start),
      endStr: formatDateTime(end),
    }
  }

  // Fetch news from DB
  const fetchNewsList = async () => {
    setLoading(true)
    const { startStr, endStr } = getTimeBounds()
    
    let url = `${backendUrl}/api/news/cls/list?limit=150`
    if (startStr) url += `&start_time=${encodeURIComponent(startStr)}`
    if (endStr) url += `&end_time=${encodeURIComponent(endStr)}`
    if (selectedCategory !== 'ALL') url += `&category=${encodeURIComponent(selectedCategory)}`

    try {
      const res = await fetch(url)
      if (res.ok) {
        const json = await res.json()
        if (json.status === 'success') {
          setNews(json.data)
        }
      }
    } catch (err) {
      console.error('Failed to fetch news:', err)
    } finally {
      setLoading(false)
    }
  }

  // Sync news from CLS endpoint
  const syncNews = async (silent = false) => {
    if (!silent) setSyncing(true)
    try {
      const res = await fetch(`${backendUrl}/api/news/cls/sync`, { method: 'POST' })
      if (res.ok) {
        const json = await res.json()
        if (json.status === 'success') {
          setLastSyncTime(new Date().toLocaleTimeString())
          // Re-fetch the list to display new items
          await fetchNewsList()
        }
      }
    } catch (err) {
      console.error('Failed to sync news:', err)
    } finally {
      if (!silent) setSyncing(false)
    }
  }

  // Call AI Analysis
  const runAiAnalysis = async (type: string) => {
    setAiLoading(true)
    setAiResult('')
    const { startStr, endStr } = getTimeBounds()

    try {
      const res = await fetch(`${backendUrl}/api/news/cls/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          start_time: startStr,
          end_time: endStr,
          analysis_type: type,
          custom_query: type === 'custom' ? customQuery : undefined,
        }),
      })

      if (res.ok) {
        const json = await res.json()
        if (json.status === 'success') {
          setAiResult(json.result)
        } else {
          setAiResult(`AI 分析失败: ${json.detail || '未知原因'}`)
        }
      } else {
        const errData = await res.json()
        setAiResult(`AI 分析发生错误: ${errData.detail || '接口异常'}`)
      }
    } catch (err: any) {
      setAiResult(`请求异常: ${err.message}`)
    } finally {
      setAiLoading(false)
    }
  }

  // Load news and set up 15-minute polling interval
  useEffect(() => {
    // Initial fetch
    fetchNewsList()
    syncNews(true)

    // Set 15-minute auto-fetch poll
    autoSyncIntervalRef.current = setInterval(() => {
      console.log('[Autosync] Fetching latest CLS news...')
      syncNews(true)
    }, 15 * 60 * 1000)

    return () => {
      if (autoSyncIntervalRef.current) {
        clearInterval(autoSyncIntervalRef.current)
      }
    }
  }, [timeRange, customStart, customEnd, selectedCategory])

  return (
    <>
      {/* ===== Header ===== */}
      <Header>
        <div className="flex items-center gap-2 font-semibold text-lg">
          <Newspaper className="h-5 w-5 text-indigo-500" />
          <span>财联社快讯决策板</span>
        </div>
        <div className="ml-auto flex items-center space-x-4">
          <ThemeSwitch />
          <ProfileDropdown />
        </div>
      </Header>

      {/* ===== Main Content ===== */}
      <Main className="space-y-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 bg-clip-text text-transparent">
              📰 财联社电报中心
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              由 SQLite 高可靠持久化存储支撑的财联社快讯大盘，支持多维度时间检索与 DeepSeek-V4-Pro 深度决策分析
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={syncing}
              onClick={() => syncNews(false)}
              className="font-bold gap-2"
            >
              {syncing ? (
                <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />
              ) : (
                <RefreshCw className="h-4 w-4 text-indigo-500" />
              )}
              {syncing ? '抓取中...' : '同步最新数据'}
            </Button>
            {lastSyncTime && (
              <Badge variant="secondary" className="text-[10px] font-mono">
                上次同步: {lastSyncTime}
              </Badge>
            )}
            <Badge variant="outline" className="px-2 py-0.5 text-xs text-emerald-500 border-emerald-500/30">
              15M 自动轮询: ON
            </Badge>
          </div>
        </div>

        {/* Filters and Search Dashboard */}
        <Card className="shadow-sm border-slate-200/80 dark:border-slate-800/80">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-bold flex items-center gap-2">
              <Search className="h-4 w-4 text-indigo-500" />
              信息筛选与区间定位
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-4 items-end">
            <div className="space-y-1">
              <label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">
                时间区间快捷键
              </label>
              <div className="flex bg-slate-100 dark:bg-slate-900 p-0.5 rounded-lg border">
                {[
                  { id: '4h', name: '4小时' },
                  { id: '12h', name: '12小时' },
                  { id: '24h', name: '24小时' },
                  { id: '3d', name: '3天内' },
                  { id: 'custom', name: '自定义' },
                ].map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setTimeRange(item.id)}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                      timeRange === item.id
                        ? 'bg-white dark:bg-black text-foreground shadow-sm'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {item.name}
                  </button>
                ))}
              </div>
            </div>

            {timeRange === 'custom' && (
              <div className="flex gap-2 items-center">
                <div className="space-y-1">
                  <label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest block">
                    开始时间
                  </label>
                  <Input
                    type="datetime-local"
                    value={customStart}
                    onChange={(e) => setCustomStart(e.target.value)}
                    className="h-9 text-xs"
                  />
                </div>
                <span className="text-muted-foreground text-xs self-end mb-2">至</span>
                <div className="space-y-1">
                  <label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest block">
                    结束时间
                  </label>
                  <Input
                    type="datetime-local"
                    value={customEnd}
                    onChange={(e) => setCustomEnd(e.target.value)}
                    className="h-9 text-xs"
                  />
                </div>
              </div>
            )}

            <div className="space-y-1">
              <label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest block">
                核心板块过滤
              </label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="h-9 px-3 text-xs rounded-lg outline-none border border-slate-200 dark:border-slate-800 bg-transparent focus:border-indigo-500/50"
              >
                <option value="ALL">全部板块</option>
                <option value="MACRO">系统与宏观 (MACRO)</option>
                <option value="US_STOCKS">美股板块 (US_STOCKS)</option>
                <option value="US_BONDS">美债与利率 (US_BONDS)</option>
                <option value="COMMODITIES">大宗与黄金 (COMMODITIES)</option>
                <option value="CN_STOCKS">中国资产 (CN_STOCKS)</option>
                <option value="EM_CRYPTO">加密与新兴 (EM_CRYPTO)</option>
                <option value="OTHER">地缘与前沿 (OTHER)</option>
              </select>
            </div>

            <Button
              variant="secondary"
              size="sm"
              onClick={fetchNewsList}
              disabled={loading}
              className="h-9 font-semibold text-xs ml-auto px-4"
            >
              <Search className="h-3 w-3 mr-2" />
              重新检索
            </Button>
          </CardContent>
        </Card>

        {/* Split Screen for News list and AI Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: News stream (8 cols) */}
          <div className="lg:col-span-6 space-y-4">
            <Card className="shadow-lg border-slate-200/80 dark:border-slate-800/80">
              <CardHeader className="pb-3 flex flex-row items-center justify-between border-b">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Clock className="text-indigo-500 h-5 w-5" />
                    电报流水线 ({news.length} 条)
                  </CardTitle>
                  <CardDescription>时间降序排列，最新的快讯永远显示在最顶部</CardDescription>
                </div>
                {loading && <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />}
              </CardHeader>
              <CardContent className="p-0">
                <div className="h-[600px] overflow-y-auto pr-1 custom-scrollbar p-4 space-y-3">
                  {news.length === 0 ? (
                    <div className="text-center py-20 text-muted-foreground italic flex flex-col items-center gap-2">
                      <Newspaper size={36} className="text-slate-600 animate-pulse" />
                      <span>该时间段内暂无快讯，尝试点击上方“同步最新数据”。</span>
                    </div>
                  ) : (
                    news.map((item) => (
                      <div
                        key={item.unique_id}
                        className={`p-4 rounded-xl border transition-all duration-300 hover:translate-x-1 ${
                          item.is_red
                            ? 'bg-rose-500/[0.03] border-rose-500/30 hover:border-rose-500/50 shadow-sm'
                            : 'bg-slate-50/50 dark:bg-slate-900/30 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-[10px] font-mono font-bold text-indigo-500 dark:text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded">
                            {item.pub_date.substring(11, 19)}
                          </span>
                          {item.is_red && (
                            <Badge variant="destructive" className="text-[9px] font-black uppercase py-0.5 px-1.5 flex items-center gap-1 animate-pulse">
                              <Flame size={10} /> 核心重点
                            </Badge>
                          )}
                          <span className="text-[10px] font-mono text-muted-foreground ml-auto bg-slate-100 dark:bg-slate-800/80 px-1.5 py-0.5 rounded">
                            {item.pub_date.substring(5, 10)}
                          </span>
                        </div>
                        {item.title && item.title !== item.content.substring(0, 30) + '...' && (
                          <h4 className={`text-sm font-bold mb-1.5 ${item.is_red ? 'text-rose-500' : 'text-slate-800 dark:text-slate-100'}`}>
                            {item.title}
                          </h4>
                        )}
                        <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-400 break-all whitespace-pre-wrap">
                          {item.content}
                        </p>
                        <div className="flex items-center gap-2 mt-3 pt-2 border-t border-slate-100 dark:border-slate-800/50 text-[10px] text-muted-foreground">
                          <span className="font-mono uppercase tracking-wider">SOURCE: {item.source}</span>
                          <span className="text-slate-300 dark:text-slate-700">|</span>
                          <span className="font-semibold">评分: {item.importance_score}分</span>
                          <span className="text-slate-300 dark:text-slate-700">|</span>
                          <span className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded font-bold">{item.asset_category}</span>
                          {item.url && (
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="ml-auto flex items-center gap-0.5 text-blue-500 hover:text-blue-400 transition-colors"
                            >
                              原文 <ExternalLink size={10} />
                            </a>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Column: AI Workspace (6 cols) */}
          <div className="lg:col-span-6 space-y-4">
            <Card className="shadow-lg border-slate-200/80 dark:border-slate-800/80 flex flex-col">
              <CardHeader className="pb-3 border-b">
                <CardTitle className="text-base flex items-center gap-2">
                  <Brain className="text-purple-500 h-5 w-5" />
                  DeepSeek 研判工作台
                </CardTitle>
                <CardDescription>结合选定时间内的快讯进行语义分析、极端行情筛选及自定义提问</CardDescription>
              </CardHeader>
              <CardContent className="p-6 space-y-6 flex-1 flex flex-col">
                {/* AI control buttons */}
                <div className="grid grid-cols-3 gap-2">
                  <Button
                    onClick={() => runAiAnalysis('top5')}
                    disabled={aiLoading || news.length === 0}
                    className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white text-[11px] font-bold py-5 px-1 shadow-sm"
                  >
                    {aiLoading ? (
                      <Loader2 className="h-3 w-3 animate-spin mr-1" />
                    ) : (
                      <Zap className="h-3 w-3 mr-1 text-amber-300 fill-amber-300" />
                    )}
                    Top 5 新闻总结
                  </Button>
                  <Button
                    onClick={() => runAiAnalysis('extreme')}
                    disabled={aiLoading || news.length === 0}
                    className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white text-[11px] font-bold py-5 px-1 shadow-sm"
                  >
                    {aiLoading ? (
                      <Loader2 className="h-3 w-3 animate-spin mr-1" />
                    ) : (
                      <TrendingDown className="h-3 w-3 mr-1 text-rose-300" />
                    )}
                    极端行情研判
                  </Button>
                  <Button
                    onClick={() => runAiAnalysis('global_assets')}
                    disabled={aiLoading || news.length === 0}
                    className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white text-[11px] font-bold py-5 px-1 shadow-sm"
                  >
                    {aiLoading ? (
                      <Loader2 className="h-3 w-3 animate-spin mr-1" />
                    ) : (
                      <Globe className="h-3 w-3 mr-1 text-sky-200" />
                    )}
                    全球资产波动
                  </Button>
                </div>

                {/* Custom semantic ask */}
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest block">
                    自定义提问研判
                  </label>
                  <div className="flex gap-2">
                    <Input
                      type="text"
                      placeholder="结合当前时间段内的资讯提问（如：A股房地产政策有何重大变化？）"
                      value={customQuery}
                      onChange={(e) => setCustomQuery(e.target.value)}
                      disabled={aiLoading || news.length === 0}
                      className="text-xs"
                      onKeyDown={(e) => e.key === 'Enter' && runAiAnalysis('custom')}
                    />
                    <Button
                      onClick={() => runAiAnalysis('custom')}
                      disabled={aiLoading || !customQuery || news.length === 0}
                      className="bg-indigo-600 hover:bg-indigo-700 text-white"
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                {/* AI Result Area */}
                <div className="flex-1 flex flex-col bg-slate-50 dark:bg-slate-950 rounded-xl border p-4 min-h-[350px] overflow-hidden">
                  <div className="text-[10px] font-black text-muted-foreground uppercase tracking-widest border-b pb-2 mb-3 flex items-center justify-between">
                    <span>研判报告分析区</span>
                    {aiLoading && <span className="text-purple-500 animate-pulse font-bold">DeepSeek 正在推理分析中...</span>}
                  </div>
                  
                  <div className="flex-1 overflow-y-auto pr-1 custom-scrollbar text-xs leading-relaxed text-slate-800 dark:text-slate-300">
                    {aiLoading ? (
                      <div className="h-full flex flex-col items-center justify-center space-y-3 pt-20">
                        <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
                        <p className="text-xs text-muted-foreground italic font-semibold">大模型正在地毯式解析电报流并提取共识逻辑...</p>
                      </div>
                    ) : aiResult ? (
                      <div className="prose prose-sm dark:prose-invert max-w-none text-slate-700 dark:text-slate-300 break-words whitespace-pre-wrap">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{aiResult}</ReactMarkdown>
                      </div>
                    ) : (
                      <div className="text-center py-20 text-muted-foreground italic flex flex-col items-center gap-2">
                        <Brain className="text-slate-600 h-8 w-8 animate-pulse" />
                        <span>等待触发分析。点击上方按钮或输入问题提交至 DeepSeek。</span>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </Main>
    </>
  )
}
