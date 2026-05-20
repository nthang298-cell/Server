using System;
using System.Collections.Concurrent;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.IO;
using System.Threading;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using System.Linq;

namespace UDPServer
{
    // ─────────────────────────────────────────────────────────────
    //  Thông tin client được lưu trên Server
    // ─────────────────────────────────────────────────────────────
    class ClientInfo
    {
        public string Name { get; set; }
        public IPEndPoint EndPoint { get; set; }
        public DateTime LastSeen { get; set; }

        public ClientInfo(string name, IPEndPoint ep)
        {
            Name = name;
            EndPoint = ep;
            LastSeen = DateTime.Now;
        }
        public override string ToString() =>
            $"{Name} ({EndPoint})";
    }

    // ─────────────────────────────────────────────────────────────
    //  Giao thức trao đổi (Protocol)
    //   JOIN:<tên>         – Client đăng ký tham gia
    //   MSG:<nội dung>     – Client gửi tin nhắn
    //   QUIT               – Client thoát
    //   PING               – Client giữ kết nối sống
    //
    //  Server phản hồi:
    //   OK:<thông báo>     – Thành công
    //   ERR:<lý do>        – Lỗi
    //   BROADCAST:<text>   – Tin quảng bá đến mọi client
    //   SYS:<text>         – Thông báo hệ thống
    // ─────────────────────────────────────────────────────────────
    static class Protocol
    {
        public const string JOIN = "JOIN";
        public const string LIST = "LIST";
        public const string PRV = "PRV"; // private message: body = target|message
        public const string DISCOVER = "DISCOVER";
        public const string ADMIN = "ADMIN";
        public const string MSG = "MSG";
        public const string QUIT = "QUIT";
        public const string PING = "PING";
        public const string OK = "OK";
        public const string ERR = "ERR";
        public const string BROADCAST = "BROADCAST";
        public const string SYS = "SYS";

        public static (string cmd, string body) Parse(string raw)
        {
            int colon = raw.IndexOf(':');
            if (colon < 0)
                return (raw.Trim().ToUpper(), string.Empty);
            return (raw[..colon].Trim().ToUpper(), raw[(colon + 1)..]);
        }

        public static string Build(string cmd, string body = "")
            => string.IsNullOrEmpty(body) ? cmd : $"{cmd}:{body}";
    }

    // ─────────────────────────────────────────────────────────────
    //  Server chính
    // ─────────────────────────────────────────────────────────────
    class Server
    {
        private const int PORT = 9000;
        private const int TIMEOUT_SEC = 60;       // client timeout
        private const int CLEANUP_INTERVAL = 15_000;   // ms

        private readonly UdpClient _udp;
        private readonly ConcurrentDictionary<string, ClientInfo> _clients;
        private readonly ConcurrentDictionary<string, ClientInfo> _pending;
        // recent log/history for export
        private readonly ConcurrentQueue<string> _history;
        // key = "ip:port"
        private readonly object _consoleLock = new();
        private bool _running = true;

        public Server()
        {
            _udp = new UdpClient(PORT);
            _clients = new ConcurrentDictionary<string, ClientInfo>();
            _pending = new ConcurrentDictionary<string, ClientInfo>();
            _history = new ConcurrentQueue<string>();
        }

        // ── Điểm vào ──────────────────────────────────────────
        public void Start()
        {
            PrintBanner();

            // Luồng nhận gói UDP
            Thread receiveThread = new Thread(ReceiveLoop)
            { IsBackground = true, Name = "ReceiveThread" };

            // Luồng dọn client hết hạn
            Thread cleanupThread = new Thread(CleanupLoop)
            { IsBackground = true, Name = "CleanupThread" };

            // Luồng nhập lệnh quản trị từ bàn phím
            Thread adminThread = new Thread(AdminLoop)
            { IsBackground = true, Name = "AdminThread" };

            receiveThread.Start();
            cleanupThread.Start();
            adminThread.Start();

            Log("Server đang chạy. Nhấn [Q] hoặc gõ 'quit' để dừng.", ConsoleColor.Green);
            adminThread.Join(); // chờ admin thoát
            Shutdown();
        }

        // ── Vòng lặp nhận gói UDP (chạy trong luồng riêng) ────
        private void ReceiveLoop()
        {
            while (_running)
            {
                try
                {
                    IPEndPoint remote = new IPEndPoint(IPAddress.Any, 0);
                    byte[] data = _udp.Receive(ref remote);
                    string raw = Encoding.UTF8.GetString(data);

                    // Xử lý mỗi gói trong ThreadPool (không block ReceiveLoop)
                    ThreadPool.QueueUserWorkItem(_ => HandlePacket(raw, remote));
                }
                catch (SocketException) when (!_running) { break; }
                catch (Exception ex)
                {
                    if (_running)
                        Log($"[ReceiveLoop] Lỗi: {ex.Message}", ConsoleColor.Red);
                }
            }
        }

        // ── Xử lý từng gói tin ────────────────────────────────
        private void HandlePacket(string raw, IPEndPoint remote)
        {
            string key = EndpointKey(remote);
            var (cmd, body) = Protocol.Parse(raw);

            switch (cmd)
            {
                case Protocol.ADMIN:
                    // admin via UDP: commands like LISTPENDING, ACCEPT:<key>, REJECT:<key>
                    AdminHandlePacket(body, remote);
                    return;

                case Protocol.DISCOVER:
                    // respond to discovery with OK so client knows server endpoint
                    Send(Protocol.Build(Protocol.OK, "DISCOVER_REPLY"), remote);
                    return;

                case Protocol.JOIN:
                    HandleJoin(body.Trim(), remote, key);
                    break;

                case Protocol.LIST:
                    // return list of connected client names to requester
                    var names = string.Join(',', _clients.Values.Select(c => c.Name));
                    Send(Protocol.Build(Protocol.OK, names), remote);
                    break;

                case Protocol.PRV:
                    // body = targetName|message
                    var idx = body.IndexOf('|');
                    if (idx > 0)
                    {
                        var target = body[..idx];
                        var msg = body[(idx + 1)..];
                        foreach (var kv in _clients)
                        {
                            if (kv.Value.Name.Equals(target, StringComparison.OrdinalIgnoreCase))
                            {
                                Send(Protocol.Build(Protocol.BROADCAST, $"[PM from {EndpointKey(remote)}]: {msg}"), kv.Value.EndPoint);
                                Send(Protocol.Build(Protocol.OK, "PRV_SENT"), remote);
                                break;
                            }
                        }
                    }
                    break;

                case Protocol.MSG:
                    HandleMessage(body, remote, key);
                    break;

                case Protocol.QUIT:
                    HandleQuit(remote, key);
                    break;

                case Protocol.PING:
                    HandlePing(remote, key);
                    break;

                default:
                    Send(Protocol.Build(Protocol.ERR, $"Lệnh không hợp lệ: {cmd}"), remote);
                    break;
            }
        }

        // ── JOIN ──────────────────────────────────────────────
        private void HandleJoin(string name, IPEndPoint remote, string key)
        {
            if (string.IsNullOrWhiteSpace(name))
            {
                Send(Protocol.Build(Protocol.ERR, "Tên không được trống."), remote);
                return;
            }

            // Kiểm tra tên trùng trong clients
            foreach (var c in _clients.Values)
            {
                if (c.Name.Equals(name, StringComparison.OrdinalIgnoreCase)
                    && EndpointKey(c.EndPoint) != key)
                {
                    Send(Protocol.Build(Protocol.ERR, $"Tên '{name}' đã được sử dụng."), remote);
                    return;
                }
            }

            // Nếu đang có cùng key trong pending hoặc clients, auto-accept (reconnect)
            if (_clients.ContainsKey(key))
            {
                _clients[key].LastSeen = DateTime.Now;
                Send(Protocol.Build(Protocol.OK, $"Chào mừng lại {name}!"), remote);
                return;
            }

            // Add to pending and notify admin
            var info = new ClientInfo(name, remote);
            _pending[key] = info;
            Send(Protocol.Build(Protocol.OK, "Yêu cầu đã gửi. Đợi admin duyệt."), remote);
            Log($"[PENDING] Yêu cầu join: {info}", ConsoleColor.Yellow);
        }

        // ── MSG ───────────────────────────────────────────────
        private void HandleMessage(string body, IPEndPoint remote, string key)
        {
            if (!_clients.TryGetValue(key, out ClientInfo? sender))
            {
                Send(Protocol.Build(Protocol.ERR, "Bạn chưa đăng ký. Gửi JOIN:<tên> trước."), remote);
                return;
            }

            sender.LastSeen = DateTime.Now;
            string line = $"[{sender.Name}]: {body}";
            Log(line, ConsoleColor.White);

            // Phản hồi để client biết server đã nhận
            Send(Protocol.Build(Protocol.OK, "Đã nhận tin nhắn."), remote);

            // Quảng bá đến tất cả client khác
            Broadcast(Protocol.Build(Protocol.BROADCAST, line), exclude: key);
        }

        // ── QUIT ──────────────────────────────────────────────
        private void HandleQuit(IPEndPoint remote, string key)
        {
            if (_clients.TryRemove(key, out ClientInfo? leaver))
            {
                Send(Protocol.Build(Protocol.OK, "Tạm biệt!"), remote);
                Broadcast(Protocol.Build(Protocol.SYS, $"<<< {leaver.Name} đã rời phòng chat."), exclude: key);
                Log($"[-] {leaver} rời phòng. Tổng: {_clients.Count}", ConsoleColor.Yellow);
                PrintStatus();
            }
        }

        // ── PING ──────────────────────────────────────────────
        private void HandlePing(IPEndPoint remote, string key)
        {
            if (_clients.TryGetValue(key, out ClientInfo? c))
                c.LastSeen = DateTime.Now;
            Send(Protocol.Build(Protocol.OK, "PONG"), remote);
        }

        // ── Dọn dẹp client không còn hoạt động ───────────────
        private void CleanupLoop()
        {
            while (_running)
            {
                Thread.Sleep(CLEANUP_INTERVAL);
                var now = DateTime.Now;
                var expired = new System.Collections.Generic.List<string>();

                foreach (var kv in _clients)
                {
                    if ((now - kv.Value.LastSeen).TotalSeconds > TIMEOUT_SEC)
                        expired.Add(kv.Key);
                }

                foreach (var key in expired)
                {
                    if (_clients.TryRemove(key, out ClientInfo? gone))
                    {
                        Broadcast(Protocol.Build(Protocol.SYS,
                            $"<<< {gone.Name} đã timeout (không hoạt động)."), exclude: key);
                        Log($"[Timeout] {gone} bị xóa.", ConsoleColor.DarkYellow);
                    }
                }

                if (expired.Count > 0) PrintStatus();
            }
        }

        // ── Bảng điều khiển quản trị ──────────────────────────
        private void AdminLoop()
        {
            while (_running)
            {
                string? input = Console.ReadLine();
                if (input == null) continue;

                string cmd = input.Trim().ToLower();
                switch (cmd)
                {
                    case "quit":
                    case "q":
                        _running = false;
                        return;

                    case "list":
                        PrintStatus();
                        break;

                    case "help":
                        PrintAdminHelp();
                        break;

                    default:
                        if (cmd.StartsWith("kick "))
                        {
                            AdminKick(cmd[5..].Trim());
                        }
                        else if (cmd.StartsWith("say "))
                        {
                            AdminSay(input[4..].Trim());
                        }
                        else if (cmd == "pending")
                        {
                            AdminListPending();
                        }
                        else if (cmd.StartsWith("accept "))
                        {
                            AdminAcceptPending(cmd[7..].Trim());
                        }
                        else if (cmd.StartsWith("reject "))
                        {
                            AdminRejectPending(cmd[7..].Trim());
                        }
                        else if (cmd.StartsWith("word "))
                        {
                            AdminExportWord(cmd[5..].Trim());
                        }
                        else if (cmd.StartsWith("docx "))
                        {
                            AdminExportDocx(cmd[5..].Trim());
                        }
                        else
                        {
                            Log("Lệnh không rõ. Gõ 'help' để xem hướng dẫn.", ConsoleColor.DarkGray);
                        }
                        break;
                }
            }
        }

        private void AdminExportWord(string filename)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(filename))
                    filename = "server_export";
                if (!filename.EndsWith(".rtf", StringComparison.OrdinalIgnoreCase))
                    filename += ".rtf";

                var sb = new StringBuilder();
                sb.Append("{\\rtf1\\ansi\\deff0\n");

                foreach (var line in _history)
                {
                    string esc = line.Replace("\\", "\\\\").Replace("{", "\\{").Replace("}", "\\}");
                    sb.Append(esc).Append("\\par\n");
                }

                sb.Append("}");

                File.WriteAllText(filename, sb.ToString(), Encoding.UTF8);
                Log($"[Admin] Đã xuất lịch sử ra file: {filename}", ConsoleColor.Green);
            }
            catch (Exception ex)
            {
                Log($"[Admin] Lỗi khi xuất file: {ex.Message}", ConsoleColor.Red);
            }
        }

        private void AdminExportDocx(string filename)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(filename))
                    filename = "server_export";
                if (!filename.EndsWith(".docx", StringComparison.OrdinalIgnoreCase))
                    filename += ".docx";

                using (var mem = new MemoryStream())
                {
                    using (WordprocessingDocument word = WordprocessingDocument.Create(mem, DocumentFormat.OpenXml.WordprocessingDocumentType.Document, true))
                    {
                        var main = word.AddMainDocumentPart();
                        main.Document = new Document(new Body());

                        Body body = main.Document.Body;

                        foreach (var line in _history)
                        {
                            var p = new Paragraph(new Run(new Text(line)));
                            body.AppendChild(p);
                        }

                        main.Document.Save();
                    }

                    File.WriteAllBytes(filename, mem.ToArray());
                }

                Log($"[Admin] Đã xuất lịch sử ra file DOCX: {filename}", ConsoleColor.Green);
            }
            catch (Exception ex)
            {
                Log($"[Admin] Lỗi khi xuất DOCX: {ex.Message}", ConsoleColor.Red);
            }
        }

        private void AdminKick(string name)
        {
            foreach (var kv in _clients)
            {
                if (kv.Value.Name.Equals(name, StringComparison.OrdinalIgnoreCase))
                {
                    Send(Protocol.Build(Protocol.SYS, "Bạn đã bị kick khỏi phòng chat!"), kv.Value.EndPoint);
                    _clients.TryRemove(kv.Key, out _);
                    Broadcast(Protocol.Build(Protocol.SYS, $"<<< {name} bị kick bởi Admin."), exclude: kv.Key);
                    Log($"[Admin] Đã kick {name}.", ConsoleColor.Magenta);
                    return;
                }
            }
            Log($"[Admin] Không tìm thấy client '{name}'.", ConsoleColor.Red);
        }

        private void AdminSay(string msg)
        {
            string line = $"[Server-Admin]: {msg}";
            Log(line, ConsoleColor.Green);
            Broadcast(Protocol.Build(Protocol.BROADCAST, line));
        }

        private void AdminListPending()
        {
            lock (_consoleLock)
            {
                Console.ForegroundColor = ConsoleColor.Yellow;
                Console.WriteLine("\nPending join requests:");
                if (_pending.IsEmpty)
                    Console.WriteLine("  (none)");
                else
                {
                    foreach (var kv in _pending)
                        Console.WriteLine($"  {kv.Key} -> {kv.Value.Name}");
                }
                Console.ResetColor();
            }
        }

        private void AdminAcceptPending(string key)
        {
            if (_pending.TryRemove(key, out ClientInfo? info))
            {
                _clients[key] = info;
                Send(Protocol.Build(Protocol.OK, $"Chào mừng {info.Name}! Có {_clients.Count} client kết nối."), info.EndPoint);
                Broadcast(Protocol.Build(Protocol.SYS, $">>> {info.Name} đã tham gia phòng chat!"), exclude: key);
                Log($"[Admin] Accepted {info}", ConsoleColor.Green);
                PrintStatus();
            }
            else
            {
                Log($"[Admin] Không tìm thấy pending key: {key}", ConsoleColor.Red);
            }
        }

        private void AdminRejectPending(string key)
        {
            if (_pending.TryRemove(key, out ClientInfo? info))
            {
                Send(Protocol.Build(Protocol.ERR, "Yêu cầu bị từ chối bởi Admin."), info.EndPoint);
                Log($"[Admin] Rejected {info}", ConsoleColor.Magenta);
            }
            else
            {
                Log($"[Admin] Không tìm thấy pending key: {key}", ConsoleColor.Red);
            }
        }

        private void AdminHandlePacket(string body, IPEndPoint remote)
        {
            if (string.IsNullOrWhiteSpace(body)) return;
            var parts = body.Split(':', 2);
            var cmd = parts[0].Trim().ToUpper();
            var arg = parts.Length > 1 ? parts[1].Trim() : string.Empty;

            switch (cmd)
            {
                case "LISTPENDING":
                    var list = string.Join(',', _pending.Select(kv => kv.Key + "=" + kv.Value.Name));
                    Send(Protocol.Build(Protocol.OK, list), remote);
                    break;
                case "ACCEPT":
                    if (!string.IsNullOrEmpty(arg))
                    {
                        AdminAcceptPending(arg);
                        Send(Protocol.Build(Protocol.OK, "ACCEPTED"), remote);
                    }
                    else
                        Send(Protocol.Build(Protocol.ERR, "MISSING_KEY"), remote);
                    break;
                case "REJECT":
                    if (!string.IsNullOrEmpty(arg))
                    {
                        AdminRejectPending(arg);
                        Send(Protocol.Build(Protocol.OK, "REJECTED"), remote);
                    }
                    else
                        Send(Protocol.Build(Protocol.ERR, "MISSING_KEY"), remote);
                    break;
                default:
                    Send(Protocol.Build(Protocol.ERR, "UNKNOWN_ADMIN_CMD"), remote);
                    break;
            }
        }

        // ── Gửi/Quảng bá ──────────────────────────────────────
        private void Send(string message, IPEndPoint target)
        {
            try
            {
                byte[] data = Encoding.UTF8.GetBytes(message);
                _udp.Send(data, data.Length, target);
            }
            catch (Exception ex)
            {
                Log($"[Send] Lỗi → {target}: {ex.Message}", ConsoleColor.Red);
            }
        }

        private void Broadcast(string message, string? exclude = null)
        {
            foreach (var kv in _clients)
            {
                if (exclude != null && kv.Key == exclude) continue;
                Send(message, kv.Value.EndPoint);
            }
        }

        // ── Tiện ích ──────────────────────────────────────────
        private static string EndpointKey(IPEndPoint ep) => $"{ep.Address}:{ep.Port}";

        private void Shutdown()
        {
            Log("Server đang tắt…", ConsoleColor.Yellow);
            Broadcast(Protocol.Build(Protocol.SYS, "Server đã tắt. Tạm biệt!"));
            Thread.Sleep(500);
            try
            {
                // Export history to DOCX automatically on shutdown
                AdminExportDocx($"server_{DateTime.Now:yyyyMMdd_HHmmss}");
            }
            catch { }
            _udp.Close();
            Log("Server đã dừng.", ConsoleColor.Red);
        }

        private void PrintStatus()
        {
            lock (_consoleLock)
            {
                Console.ForegroundColor = ConsoleColor.DarkCyan;
                Console.WriteLine();
                Console.WriteLine("╔════════════════════════════════════════════════════════════════╗");
                Console.WriteLine($"║   Active Clients : {_clients.Count,-52}║");
                Console.WriteLine("╠═════════════════╦════════════════════════════════╦═════════════╣");
                Console.WriteLine("║ Name            ║ Endpoint                       ║ Last seen   ║");
                Console.WriteLine("╠═════════════════╬════════════════════════════════╬═════════════╣");

                if (_clients.IsEmpty)
                {
                    Console.WriteLine("║  (no clients)                                                   ║");
                }
                else
                {
                    foreach (var kv in _clients)
                    {
                        var c = kv.Value;
                        string name = c.Name.Length > 15 ? c.Name[..15] : c.Name.PadRight(15);
                        string ep = EndpointKey(c.EndPoint);
                        if (ep.Length > 30) ep = ep[..30];
                        string last = c.LastSeen.ToString("HH:mm:ss");
                        Console.WriteLine($"║ {name} ║ {ep.PadRight(30)} ║ {last} ║");
                    }
                }

                Console.WriteLine("╚═════════════════╩════════════════════════════════╩═════════════╝");
                Console.ResetColor();
            }
        }

        private void PrintAdminHelp()
        {
            lock (_consoleLock)
            {
                Console.ForegroundColor = ConsoleColor.DarkYellow;
                Console.WriteLine();
                Console.WriteLine("╔═════════════════════════════════════[ ADMIN COMMANDS ]════════════════════════════╗");
                Console.ResetColor();
                Console.WriteLine("  list        	– List connected clients");
                Console.WriteLine("  say <text>  	– Broadcast message to all clients");
                Console.WriteLine("  kick <name> 	– Kick a client by name");
                Console.WriteLine("  pending     	– List pending join requests");
                Console.WriteLine("  accept <key>	– Accept pending request (key = ip:port)");
                Console.WriteLine("  reject <key>	– Reject pending request");
                Console.WriteLine("  word <file> 	– Export history to RTF");
                Console.WriteLine("  docx <file> 	– Export history to .docx");
                Console.WriteLine("  help        	– Show this help");
                Console.WriteLine("  quit / q    	– Shutdown server\n");
                Console.WriteLine("╚════════════════════════════════════════════════════════════════════════════════════╝\n");
            }
        }

        private void Log(string msg, ConsoleColor color = ConsoleColor.Gray)
        {
            lock (_consoleLock)
            {
                string timestamp = DateTime.Now.ToString("HH:mm:ss");
                string full = $"[{timestamp}] {msg}";

                // store to history (bounded)
                try
                {
                    _history.Enqueue(full);
                    while (_history.Count > 1000)
                        _history.TryDequeue(out _);
                }
                catch { }

                Console.ForegroundColor = ConsoleColor.DarkGray;
                Console.Write($"[{timestamp}] ");
                Console.ForegroundColor = color;
                Console.WriteLine(msg);
                Console.ResetColor();
            }
        }

        private void PrintBanner()
        {
            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine(@"
╔══════════════════════════════════════════════════╗
║         UDP CHAT SERVER  –  C#  .NET 8           ║
║  Cổng  : 9000                                    ║
║  Giao thức: UDP / Đa luồng                       ║
╚══════════════════════════════════════════════════╝");
            Console.ResetColor();
        }
    }

    // ─────────────────────────────────────────────────────────────
    //  Entry point
    // ─────────────────────────────────────────────────────────────
    class Program
    {
        static void Main()
        {
            Console.OutputEncoding = Encoding.UTF8;
            try
            {
                new Server().Start();
            }
            catch (Exception ex)
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine($"Lỗi khởi động server: {ex.Message}");
                Console.ResetColor();
            }
        }
    }
}