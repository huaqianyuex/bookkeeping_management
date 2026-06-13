export interface Message {
  id: string;
  sessionId: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

export interface Session {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
}

export interface Feedback {
  id: string;
  messageId: string;
  rating: number;
  comment?: string;
  timestamp: number;
}

export interface FAQ {
  id: number;
  question: string;
  answer: string;
  category: string;
}

export class Database {
  private db: SqlDb | null = null;
  private dbPath: string;

  constructor() {
    this.dbPath = path.join(__dirname, '../data/chat.db');
    // 数据库将在 init() 方法中异步初始化
  }

  async init(): Promise<void> {
    const SQL = await initSqlJs();

    // 如果数据库文件存在，则加载
    if (fs.existsSync(this.dbPath)) {
      const buffer = fs.readFileSync(this.dbPath);
      this.db = new SQL.Database(buffer);
    } else {
      this.db = new SQL.Database();
    }

    this.initDatabase();
    this.initFAQ();
  }

  private save(): void {
    if (!this.db) return;
    const data = this.db.export();
    const buffer = Buffer.from(data);
    const dir = path.dirname(this.dbPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(this.dbPath, buffer);
  }

  private initDatabase(): void {
    if (!this.db) return;

    this.db.run(`
      CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
      )
    `);

    this.db.run(`
      CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp INTEGER NOT NULL
      )
    `);

    this.db.run(`
      CREATE TABLE IF NOT EXISTS feedback (
        id TEXT PRIMARY KEY,
        message_id TEXT NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        timestamp INTEGER NOT NULL
      )
    `);

    this.db.run(`
      CREATE TABLE IF NOT EXISTS faq (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        category TEXT NOT NULL
      )
    `);

    this.save();
  }

  private initFAQ(): void {
    if (!this.db) return;

    // 检查是否已有 FAQ 数据
    const result = this.db.exec('SELECT COUNT(*) as count FROM faq');
    let count = 0;
    if (result.length > 0 && result[0].values.length > 0) {
      count = result[0].values[0][0] as number;
    }

    if (count === 0) {
      const faqData = [
        ['如何添加一笔消费记录？', '您可以直接对我说："帮我记录一笔餐饮消费50元"，我会自动帮您记录。也可以说"添加支出：交通，30元"等。', '记账操作'],
        ['如何查看我的账单？', '您可以说："查看本月的账单"、"显示我的消费记录"、"这个月花了多少钱"等，我会为您展示相应的账单信息。', '账单查询'],
        ['系统支持哪些消费类型？', '我们支持多种消费类型：餐饮、交通、购物、娱乐、住房、医疗、教育、其他等。您也可以自定义消费类型。', '功能介绍'],
        ['如何设置预算？', '您可以说："设置本月预算为5000元"、"帮我制定消费预算"等，我会帮您设置并跟踪预算执行情况。', '预算管理'],
        ['数据会保存多久？', '您的记账数据会永久保存在系统中，除非您主动删除。我们重视您的数据安全。', '技术支持'],
        ['如何导出账单？', '目前支持导出为 CSV 格式。您可以说："导出本月账单为 CSV"、"下载我的消费记录"等。', '数据管理']
      ];

      const stmt = this.db.prepare('INSERT INTO faq (question, answer, category) VALUES (?, ?, ?)');
      for (const faq of faqData) {
        stmt.run(faq);
      }
      stmt.free();
      this.save();
    }
  }

  // ==================== 会话操作 ====================

  createSession(title: string): string {
    if (!this.db) throw new Error('数据库未初始化');

    const id = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const now = Date.now();

    this.db.run('INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)', [id, title, now, now]);
    this.save();

    return id;
  }

  getAllSessions(): Session[] {
    if (!this.db) return [];

    const result = this.db.exec('SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC');
    if (result.length === 0) return [];

    return result[0].values.map((row: any[]) => ({
      id: row[0] as string,
      title: row[1] as string,
      createdAt: row[2] as number,
      updatedAt: row[3] as number,
    }));
  }

  getSession(id: string): Session | undefined {
    if (!this.db) return undefined;

    const stmt = this.db.prepare('SELECT id, title, created_at, updated_at FROM sessions WHERE id = ?');
    stmt.bind([id]);
    let session: Session | undefined;

    while (stmt.step()) {
      const row = stmt.getAsObject();
      session = {
        id: row.id as string,
        title: row.title as string,
        createdAt: row.created_at as number,
        updatedAt: row.updated_at as number,
      };
      break;
    }
    stmt.free();

    return session;
  }

  deleteSession(id: string): void {
    if (!this.db) return;

    this.db.run('DELETE FROM messages WHERE session_id = ?', [id]);
    this.db.run('DELETE FROM sessions WHERE id = ?', [id]);
    this.save();
  }

  // ==================== 消息操作 ====================

  addMessage(sessionId: string, role: 'user' | 'assistant', content: string): string {
    if (!this.db) throw new Error('数据库未初始化');

    const id = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const timestamp = Date.now();

    this.db.run('INSERT INTO messages (id, session_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)', [id, sessionId, role, content, timestamp]);
    this.db.run('UPDATE sessions SET updated_at = ? WHERE id = ?', [timestamp, sessionId]);
    this.save();

    return id;
  }

  getSessionMessages(sessionId: string): Message[] {
    if (!this.db) return [];

    const result = this.db.exec(`SELECT id, session_id, role, content, timestamp FROM messages WHERE session_id = '${sessionId}' ORDER BY timestamp ASC`);
    if (result.length === 0) return [];

    return result[0].values.map((row: any[]) => ({
      id: row[0] as string,
      sessionId: row[1] as string,
      role: row[2] as string,
      content: row[3] as string,
      timestamp: row[4] as number,
    })) as Message[];
  }

  // ==================== FAQ 操作 ====================

  searchFAQ(query: string): FAQ[] {
    if (!this.db) return [];

    const searchTerm = `%${query}%`;
    const result = this.db.exec(`SELECT id, question, answer, category FROM faq WHERE question LIKE '${searchTerm}' OR answer LIKE '${searchTerm}' LIMIT 5`);
    if (result.length === 0) return [];

    return result[0].values.map((row: any[]) => ({
      id: row[0] as number,
      question: row[1] as string,
      answer: row[2] as string,
      category: row[3] as string,
    }));
  }

  // ==================== 反馈操作 ====================

  addFeedback(messageId: string, rating: number, comment?: string): void {
    if (!this.db) return;

    const id = `feedback_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const timestamp = Date.now();

    this.db.run('INSERT INTO feedback (id, message_id, rating, comment, timestamp) VALUES (?, ?, ?, ?, ?)', [id, messageId, rating, comment || null, timestamp]);
    this.save();
  }

  // ==================== 统计操作 ====================

  getChatStats(): any {
    if (!this.db) {
      return { totalSessions: 0, totalMessages: 0, totalFeedback: 0, averageRating: 0 };
    }

    const sessionResult = this.db.exec('SELECT COUNT(*) as count FROM sessions');
    const msgResult = this.db.exec('SELECT COUNT(*) as count FROM messages');
    const feedbackResult = this.db.exec('SELECT COUNT(*) as count FROM feedback');
    const avgResult = this.db.exec('SELECT AVG(rating) as avg FROM feedback');

    const totalSessions = sessionResult.length > 0 && sessionResult[0].values.length > 0 ? sessionResult[0].values[0][0] as number : 0;
    const totalMessages = msgResult.length > 0 && msgResult[0].values.length > 0 ? msgResult[0].values[0][0] as number : 0;
    const totalFeedback = feedbackResult.length > 0 && feedbackResult[0].values.length > 0 ? feedbackResult[0].values[0][0] as number : 0;
    const avgRating = avgResult.length > 0 && avgResult[0].values.length > 0 && avgResult[0].values[0][0] !== null ? avgResult[0].values[0][0] as number : 0;

    return {
      totalSessions,
      totalMessages,
      totalFeedback,
      averageRating: avgRating
    };
  }

  getAllConversations(page: number, limit: number): any {
    if (!this.db) {
      return { conversations: [], pagination: { page, limit, total: 0, totalPages: 0 } };
    }

    const offset = (page - 1) * limit;

    const result = this.db.exec(`
      SELECT
        s.id as sessionId,
        s.title,
        s.created_at as createdAt,
        s.updated_at as updatedAt,
        COUNT(m.id) as messageCount
      FROM sessions s
      LEFT JOIN messages m ON s.id = m.session_id
      GROUP BY s.id
      ORDER BY s.updated_at DESC
      LIMIT ${limit} OFFSET ${offset}
    `);

    const totalResult = this.db.exec('SELECT COUNT(*) as count FROM sessions');
    const total = totalResult.length > 0 && totalResult[0].values.length > 0 ? totalResult[0].values[0][0] as number : 0;

    const conversations = result.length > 0 ? result[0].values.map((row: any[]) => ({
      sessionId: row[0] as string,
      title: row[1] as string,
      createdAt: row[2] as number,
      updatedAt: row[3] as number,
      messageCount: row[4] as number,
    })) : [];

    return {
      conversations,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit)
      }
    };
  }

  getSatisfactionStats(): any {
    if (!this.db) {
      return { distribution: [], recentFeedback: [] };
    }

    const distResult = this.db.exec(`
      SELECT rating, COUNT(*) as count
      FROM feedback
      GROUP BY rating
      ORDER BY rating
    `);

    const recentResult = this.db.exec(`
      SELECT f.id, f.message_id, f.rating, f.comment, f.timestamp, m.content
      FROM feedback f
      LEFT JOIN messages m ON f.message_id = m.id
      ORDER BY f.timestamp DESC
      LIMIT 20
    `);

    const distribution = distResult.length > 0 ? distResult[0].values.map((row: any[]) => ({
      rating: row[0] as number,
      count: row[1] as number,
    })) : [];

    const recentFeedback = recentResult.length > 0 ? recentResult[0].values.map((row: any[]) => ({
      id: row[0] as string,
      messageId: row[1] as string,
      rating: row[2] as number,
      comment: row[3] as string || undefined,
      timestamp: row[4] as number,
      messageContent: row[5] as string || '',
    })) : [];

    return {
      distribution,
      recentFeedback
    };
  }

  close(): void {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
  }
}
