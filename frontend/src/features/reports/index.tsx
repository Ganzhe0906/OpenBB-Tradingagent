import { useState, useEffect } from 'react'
import {
  FileText,
  Search,
  RefreshCw,
  Download,
  Calendar,
  Layers,
  ChevronRight,
  LineChart,
  Globe,
  Newspaper,
  Trash2,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { ThemeSwitch } from '@/components/theme-switch'
import { ProfileDropdown } from '@/components/profile-dropdown'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'

interface ReportItem {
  filename: string
  date: string
  ticker: string
}

interface ReportContent {
  filename: string
  content: string
}

export function Reports() {
  const [reports, setReports] = useState<ReportItem[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFilename, setSelectedFilename] = useState<string | null>(null)
  const [reportContent, setReportContent] = useState<ReportContent | null>(null)
  const [isLoadingList, setIsLoadingList] = useState(false)
  const [isLoadingContent, setIsLoadingContent] = useState(false)

  // Delete modal state
  const [reportToDelete, setReportToDelete] = useState<string | null>(null)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)

  const backendUrl = 'http://127.0.0.1:8000'

  // Fetch report list
  const fetchReportsList = async (selectFirst = false) => {
    setIsLoadingList(true)
    try {
      const res = await fetch(`${backendUrl}/api/reports`)
      if (res.ok) {
        const data = await res.json()
        setReports(data)
        if (selectFirst && data.length > 0) {
          setSelectedFilename(data[0].filename)
        }
      }
    } catch (err) {
      console.error('Failed to fetch reports list:', err)
    } finally {
      setIsLoadingList(false)
    }
  }

  // Fetch specific report content
  const fetchReportContent = async (filename: string) => {
    setIsLoadingContent(true)
    try {
      const res = await fetch(`${backendUrl}/api/reports/${filename}`)
      if (res.ok) {
        const data = await res.json()
        setReportContent(data)
      }
    } catch (err) {
      console.error('Failed to fetch report content:', err)
    } finally {
      setIsLoadingContent(false)
    }
  }

  useEffect(() => {
    fetchReportsList(true)
  }, [])

  useEffect(() => {
    if (selectedFilename) {
      fetchReportContent(selectedFilename)
    } else {
      setReportContent(null)
    }
  }, [selectedFilename])

  // Filter reports by search query
  const filteredReports = reports.filter((report) => {
    const term = searchQuery.toLowerCase()
    return (
      report.ticker.toLowerCase().includes(term) ||
      report.date.toLowerCase().includes(term) ||
      report.filename.toLowerCase().includes(term)
    )
  })

  // Download raw markdown report
  const downloadReport = () => {
    if (!reportContent) return
    const element = document.createElement('a')
    const file = new Blob([reportContent.content], { type: 'text/markdown;charset=utf-8' })
    element.href = URL.createObjectURL(file)
    element.download = reportContent.filename
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
  }

  // Delete a report
  const deleteReport = async (filename: string) => {
    try {
      const res = await fetch(`${backendUrl}/api/reports/${filename}`, {
        method: 'DELETE',
      })
      if (res.ok) {
        // Clear selection first
        setSelectedFilename(null)
        setReportContent(null)
        // Refresh list
        await fetchReportsList(true)
      } else {
        console.error('Failed to delete report')
      }
    } catch (err) {
      console.error('Error deleting report:', err)
    }
  }

  // Markdown custom renderer components for premium layout style
  const markdownComponents = {
    h1: ({ ...props }) => (
      <h1
        className='text-2xl font-extrabold border-b pb-2 mb-6 mt-8 text-indigo-600 dark:text-indigo-400 tracking-tight'
        {...props}
      />
    ),
    h2: ({ ...props }) => (
      <h2
        className='text-xl font-bold border-l-4 border-indigo-500 pl-3 my-5 text-slate-800 dark:text-slate-200 tracking-tight'
        {...props}
      />
    ),
    h3: ({ ...props }) => (
      <h3
        className='text-lg font-bold mt-5 mb-2.5 text-slate-800 dark:text-slate-300'
        {...props}
      />
    ),
    p: ({ ...props }) => (
      <p
        className='text-sm leading-relaxed mb-4 text-slate-600 dark:text-slate-400'
        {...props}
      />
    ),
    ul: ({ ...props }) => (
      <ul className='list-disc pl-6 mb-4 space-y-1 text-slate-600 dark:text-slate-400' {...props} />
    ),
    ol: ({ ...props }) => (
      <ol className='list-decimal pl-6 mb-4 space-y-1 text-slate-600 dark:text-slate-400' {...props} />
    ),
    li: ({ ...props }) => <li className='text-sm' {...props} />,
    blockquote: ({ ...props }) => (
      <div
        className='border-l-4 border-purple-500 pl-4 py-2 italic bg-purple-50/30 dark:bg-purple-950/10 my-4 rounded-r-lg text-sm text-slate-700 dark:text-slate-300'
        {...props}
      />
    ),
    table: ({ ...props }) => (
      <div className='w-full overflow-x-auto my-6 border rounded-lg shadow-sm'>
        <table className='w-full border-collapse text-sm' {...props} />
      </div>
    ),
    thead: ({ ...props }) => <thead className='bg-slate-50 dark:bg-slate-900 border-b' {...props} />,
    tbody: ({ ...props }) => <tbody className='divide-y' {...props} />,
    tr: ({ ...props }) => <tr className='hover:bg-slate-50/50 dark:hover:bg-slate-900/30' {...props} />,
    th: ({ ...props }) => (
      <th
        className='font-semibold p-3 text-left text-slate-800 dark:text-slate-200'
        {...props}
      />
    ),
    td: ({ ...props }) => <td className='p-3 text-slate-600 dark:text-slate-400' {...props} />,
    code: ({ ...props }) => (
      <code
        className='bg-slate-100 dark:bg-slate-900 px-1.5 py-0.5 rounded font-mono text-xs text-rose-600 dark:text-rose-400'
        {...props}
      />
    ),
    pre: ({ ...props }) => (
      <pre
        className='bg-slate-950 dark:bg-black text-slate-100 p-4 rounded-lg my-6 overflow-x-auto font-mono text-xs shadow-inner'
        {...props}
      />
    ),
  }

  return (
    <>
      {/* ===== Top Heading ===== */}
      <Header>
        <div className='flex items-center gap-2 font-semibold text-lg'>
          <FileText className='h-5 w-5 text-indigo-500' />
          <span>最新决策分析报告</span>
        </div>
        <div className='ml-auto flex items-center space-x-4'>
          <ThemeSwitch />
          <ProfileDropdown />
        </div>
      </Header>

      {/* ===== Main Content ===== */}
      <Main className='h-[calc(100vh-100px)] p-0 flex flex-col'>
        <div className='flex-1 flex overflow-hidden border-t dark:border-slate-800'>
          
          {/* Left Pane: Report Sidebar List */}
          <div className='w-80 border-r dark:border-slate-800 flex flex-col bg-slate-50/50 dark:bg-slate-900/10 min-w-[280px]'>
            <div className='p-4 border-b dark:border-slate-800 space-y-3'>
              <div className='flex items-center justify-between'>
                <h3 className='font-bold text-sm tracking-tight text-slate-800 dark:text-slate-200'>
                  历史分析报告 ({filteredReports.length})
                </h3>
                <Button
                  variant='ghost'
                  size='icon'
                  onClick={() => fetchReportsList(false)}
                  disabled={isLoadingList}
                  className='h-7 w-7'
                >
                  <RefreshCw
                    className={`h-3.5 w-3.5 ${isLoadingList ? 'animate-spin' : ''}`}
                  />
                </Button>
              </div>
              <div className='relative'>
                <Search className='absolute left-3 top-2.5 h-4 w-4 text-muted-foreground' />
                <Input
                  placeholder='搜索代码/日期...'
                  className='pl-9 h-9 text-xs'
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            <div className='flex-1 overflow-y-auto p-2'>
              {isLoadingList ? (
                <div className='text-center py-8 text-xs text-muted-foreground italic'>
                  加载列表中...
                </div>
              ) : filteredReports.length === 0 ? (
                <div className='text-center py-8 text-xs text-muted-foreground italic'>
                  无匹配报告
                </div>
              ) : (
                <div className='space-y-1'>
                  {filteredReports.map((report) => {
                    const isSelected = selectedFilename === report.filename
                    const isMacro = report.ticker.startsWith('MACRO-')
                    const isCls = report.ticker.startsWith('CLS_')
                    
                    const getReportTitle = (ticker: string) => {
                      if (ticker.startsWith('MACRO-')) {
                        const type = ticker.replace('MACRO-', '').toUpperCase()
                        const titles: Record<string, string> = {
                          WEEKLY_FLOW: '跨市场资金流向 (周度)',
                          DAILY_REVIEW: '24小时全球大势锐评',
                          RISK_QUANT: '大类资产水位与风险量化',
                          WATCHLIST_MONITOR: '核心自选资产最新动向',
                        }
                        return titles[type] || `宏观研判 (${type})`
                      }
                      if (ticker.startsWith('CLS_')) {
                        const parts = ticker.split('_')
                        const type = parts[1] || ''
                        const timeStr = parts[2] || ''
                        const formattedTime = timeStr ? `${timeStr.substring(0, 2)}:${timeStr.substring(2, 4)}:${timeStr.substring(4, 6)}` : ''
                        
                        const types: Record<string, string> = {
                          top5: '财联社 Top 5 核心快讯总结',
                          extreme: '财联社 极端行情分析报告',
                          custom: '财联社 自定义快讯研判',
                        }
                        
                        const typeName = types[type] || `财联社 智能分析 (${type})`
                        return formattedTime ? `${typeName} (${formattedTime})` : typeName
                      }
                      return `${ticker} 决策研判报告`
                    }

                    return (
                      <button
                        key={report.filename}
                        onClick={() => setSelectedFilename(report.filename)}
                        className={`w-full text-left p-3 rounded-lg flex items-center justify-between transition-all duration-200 ${
                          isSelected
                            ? 'bg-indigo-50 dark:bg-indigo-950/30 border-l-4 border-indigo-500 shadow-sm'
                            : 'hover:bg-slate-100 dark:hover:bg-slate-900 border-l-4 border-transparent'
                        }`}
                      >
                        <div className='flex items-center gap-3 overflow-hidden'>
                          <div
                            className={`p-1.5 rounded-md ${
                              isSelected
                                ? isMacro 
                                  ? 'bg-purple-100 text-purple-600 dark:bg-purple-900 dark:text-purple-300'
                                  : isCls
                                    ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900 dark:text-emerald-300'
                                    : 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900 dark:text-indigo-300'
                                : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                            }`}
                          >
                            {isMacro ? (
                              <Globe className='h-4 w-4' />
                            ) : isCls ? (
                              <Newspaper className='h-4 w-4' />
                            ) : (
                              <LineChart className='h-4 w-4' />
                            )}
                          </div>
                          <div className='overflow-hidden'>
                            <div className='font-bold text-xs text-slate-800 dark:text-slate-200 uppercase truncate'>
                              {getReportTitle(report.ticker)}
                            </div>
                            <div className='text-[10px] text-muted-foreground flex items-center gap-1 mt-0.5'>
                              <Calendar className='h-3 w-3' />
                              <span>{report.date}</span>
                            </div>
                          </div>
                        </div>
                        <ChevronRight
                          className={`h-4 w-4 transition-transform ${
                            isSelected
                              ? 'text-indigo-500 translate-x-0.5'
                              : 'text-slate-400'
                          }`}
                        />
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Right Pane: Report Reader Content */}
          <div className='flex-1 flex flex-col overflow-hidden bg-white dark:bg-slate-950'>
            {isLoadingContent ? (
              <div className='flex-1 flex flex-col items-center justify-center text-slate-400 italic gap-3'>
                <RefreshCw className='h-8 w-8 text-indigo-500 animate-spin' />
                <span className='text-sm'>正在载入报告详情...</span>
              </div>
            ) : reportContent ? (
              <div className='flex-1 flex flex-col overflow-hidden'>
                {/* Reader Toolbar */}
                <div className='px-6 py-4 border-b dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/10'>
                  <div>
                    <h2 className='text-md font-bold text-slate-800 dark:text-slate-100 uppercase tracking-tight flex items-center gap-2'>
                      <Layers className='h-4 w-4 text-purple-500' />
                      {reportContent.filename.replace('.md', '')}
                    </h2>
                    <p className='text-xs text-muted-foreground mt-0.5'>
                      多智能体深度分析共识文件
                    </p>
                  </div>
                  <div className='flex items-center gap-2'>
                    <Button
                      variant='outline'
                      size='sm'
                      className='text-xs flex items-center gap-2 border-slate-300 dark:border-slate-700'
                      onClick={downloadReport}
                    >
                      <Download className='h-3.5 w-3.5' />
                      下载 Markdown
                    </Button>
                    <Button
                      variant='destructive'
                      size='sm'
                      className='text-xs flex items-center gap-2'
                      onClick={() => {
                        setReportToDelete(reportContent.filename)
                        setIsDeleteDialogOpen(true)
                      }}
                    >
                      <Trash2 className='h-3.5 w-3.5' />
                      删除报告
                    </Button>
                  </div>
                </div>

                {/* Markdown Reader Body */}
                <div className='flex-1 overflow-y-auto px-8 py-6 bg-white dark:bg-slate-950/50'>
                  <article className='max-w-3xl mx-auto pb-12 text-slate-800 dark:text-slate-200'>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={markdownComponents}
                    >
                      {reportContent.content}
                    </ReactMarkdown>
                  </article>
                </div>
              </div>
            ) : (
              <div className='flex-1 flex flex-col items-center justify-center text-slate-400 italic gap-3'>
                <FileText className='h-12 w-12 text-slate-300 dark:text-slate-800' />
                <span className='text-sm'>请在左侧侧边栏中选择一份报告以进行查阅。</span>
              </div>
            )}
          </div>
        </div>
      </Main>
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除决策报告？</AlertDialogTitle>
            <AlertDialogDescription>
              此操作将永久删除报告文件 <code className='text-rose-600 font-mono'>{reportToDelete}</code> 且不可恢复。本地磁盘上的 markdown 文件也将被同步清理。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              className='bg-destructive hover:bg-destructive/90 text-destructive-foreground border border-transparent'
              onClick={() => {
                if (reportToDelete) {
                  deleteReport(reportToDelete)
                }
                setIsDeleteDialogOpen(false)
              }}
            >
              确认删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
