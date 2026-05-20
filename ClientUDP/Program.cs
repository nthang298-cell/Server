using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Collections.Concurrent;
using System.IO;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;

namespace UDPClient
{
    // ─────────────────────────────────────────────────────────────
    //  Trạng thái kết nối
    // ─────────────────────────────────────────────────────────────
    enum ConnectionState { Disconnected, Connecting, Connected }

    // ─────────────────────────────────────────────────────────────
    //  Giao thức – giống bên Server (giữ đồng bộ)
    // ─────────────────────────────────────────────────────────────
    static class Protocol
    {
        public const string JOIN = "JOIN";
        public const string DISCOVER = "DISCOVER";
        public const string LIST = "LIST";
        public const string PRV = "PRV";
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
            if (colon < 0) return (raw.Trim().ToUpper(), string.Empty);
            return (raw[..colon].Trim().ToUpper(), raw[(colon + 1)..]);
        }

        public static string Build(string cmd, string body = "")
            => string.IsNullOrEmpty(body) ? cmd : $"{cmd}:{body}";
    }

    // ─────────────────────────────────────────────────────────────
    //  Client chính
    // ─────────────────────────────────────────────────────────────
    class Client
    {
        // ── Cấu hình mặc định ─────────────────────────────────
        private string _serverIP = "127.0.0.1";
        private int _serverPort = 9000;
        private string _nickname = string.Empty;

        // ── Trạng thái ────────────────────────────────────────
        private UdpClient? _udp;
        private IPEndPoint? _serverEP;
        private ConnectionState _state = ConnectionState.Disconnected;
        private bool _running = false;
        private int _pingInterval = 20_000; // ms
        private readonly ConcurrentQueue<string> _history = new();
        private bool _autoReconnect = false;

        private readonly object _consoleLock = new();
        private readonly System.Collections.Generic.List<(string name, string ip, int port)> _servers = new();

        // ─────────────────────────────────────────────────────
        //  Điểm vào
        // ─────────────────────────────────────────────────────
        public void Start()
        {
            Console.OutputEncoding = Encoding.UTF8;
            PrintBanner();
            MainMenu();
        }

        // ── Menu chính ────────────────────────────────────────
        private void MainMenu()
        {
            // Luxury-styled main menu with status panel
            int width = 62;
            while (true)
            {
                Console.Clear();
                Console.ForegroundColor = ConsoleColor.DarkMagenta;
                Console.WriteLine("╔" + new string('═', width - 2) + "╗");
                Console.WriteLine("║" + CenterText("✨  LUXURY UDP CHAT CLIENT  ✨", width - 2) + "║");
                Console.WriteLine("╠" + new string('═', width - 2) + "╣");

                // status panel
                Console.ForegroundColor = ConsoleColor.DarkCyan;
                Console.WriteLine("║" + CenterText($"Server: {_serverIP}:{_serverPort}", width - 2) + "║");
                Console.WriteLine("║" + CenterText($"Nick: {_nickname}    Ping: {_pingInterval}ms    AutoReconnect: {(_autoReconnect ? "ON" : "OFF")}", width - 2) + "║");
                Console.WriteLine("╠" + new string('═', width - 2) + "╣");

                Console.ResetColor();
                Console.WriteLine("║ 1) Kết nối Server".PadRight(width - 1) + "║");
                Console.WriteLine("║ 2) Cấu hình".PadRight(width - 1) + "║");
                Console.WriteLine("║ 3) Quản lý Server".PadRight(width - 1) + "║");
                Console.WriteLine("║ 4) Tiện ích (Utilities)".PadRight(width - 1) + "║");
                Console.WriteLine("║ 5) Thoát".PadRight(width - 1) + "║");

                Console.ForegroundColor = ConsoleColor.DarkMagenta;
                Console.WriteLine("╚" + new string('═', width - 2) + "╝");
                Console.ResetColor();

                Console.Write("Chọn: ");
                string? choice = Console.ReadLine()?.Trim();
                switch (choice)
                {
                    case "1": ConnectFlow(); break;
                    case "2": ConfigFlow(); break;
                    case "3": ManageServersMenu(); break;
                    case "4": UtilitiesMenu(); break;
                    case "5": Console.WriteLine("Tạm biệt!"); return;
                    default: Log("Lựa chọn không hợp lệ.", ConsoleColor.Red); Thread.Sleep(800); break;
                }
            }
        }

        private void ManageServersMenu()
        {
            while (true)
            {
                Console.ForegroundColor = ConsoleColor.DarkBlue;
                Console.WriteLine("\n--- QUẢN LÝ SERVER ---");
                Console.ResetColor();
                Console.WriteLine(" 1. Thêm server (IP:Port)");
                Console.WriteLine(" 2. Chọn server mặc định");
                Console.WriteLine(" 3. Liệt kê client trên server đã chọn");
                Console.WriteLine(" 4. Gửi tin nhắn riêng tới client (qua server)");
                Console.WriteLine(" 5. Quay lại");
                Console.Write("Chọn: ");
                string? c = Console.ReadLine()?.Trim();
                switch (c)
                {
                    case "1":
                        Console.Write("IP hoặc tên server: ");
                        string? ip = Console.ReadLine()?.Trim();
                        Console.Write("Port [9000]: ");
                        string? p = Console.ReadLine()?.Trim();
                        int port = 9000;
                        if (!string.IsNullOrEmpty(p) && int.TryParse(p, out int pv)) port = pv;
                        if (!string.IsNullOrEmpty(ip))
                        {
                            _servers.Add((ip, ip, port));
                            Log($"Added server {ip}:{port}", ConsoleColor.Green);
                        }
                        break;
                    case "2":
                        if (_servers.Count == 0) { Log("Chưa có server nào.", ConsoleColor.Yellow); break; }
                        for (int i = 0; i < _servers.Count; i++) Console.WriteLine($" {i+1}. {_servers[i].ip}:{_servers[i].port}");
                        Console.Write("Chọn số: ");
                        string? sel = Console.ReadLine()?.Trim();
                        if (int.TryParse(sel, out int si) && si >= 1 && si <= _servers.Count)
                        {
                            var s = _servers[si - 1];
                            _serverIP = s.ip; _serverPort = s.port;
                            Log($"Selected server {_serverIP}:{_serverPort}", ConsoleColor.Cyan);
                        }
                        break;
                    case "3":
                        ListClientsOnServer();
                        break;
                    case "4":
                        SendPrivateViaServer();
                        break;
                    case "5": return;
                    default: Log("Lựa chọn không hợp lệ.", ConsoleColor.Red); break;
                }
            }
        }

        private void ListClientsOnServer()
        {
            try
            {
                using var c = new UdpClient();
                var ep = new IPEndPoint(IPAddress.Parse(_serverIP), _serverPort);
                var msg = Encoding.UTF8.GetBytes(Protocol.Build(Protocol.LIST));
                c.Send(msg, msg.Length, ep);
                c.Client.ReceiveTimeout = 2000;
                var any = new IPEndPoint(IPAddress.Any, 0);
                byte[] resp = c.Receive(ref any);
                var (cmd, body) = Protocol.Parse(Encoding.UTF8.GetString(resp));
                if (cmd == Protocol.OK)
                {
                    if (string.IsNullOrEmpty(body)) Log("(không có client)", ConsoleColor.Yellow);
                    else
                    {
                        var names = body.Split(',', StringSplitOptions.RemoveEmptyEntries);
                        Log("Clients:", ConsoleColor.Cyan);
                        foreach (var n in names) Console.WriteLine($" - {n}");
                    }
                }
            }
            catch (Exception ex) { Log($"Lỗi: {ex.Message}", ConsoleColor.Red); }
        }

        private void SendPrivateViaServer()
        {
            Console.Write("Tên người nhận: ");
            string? target = Console.ReadLine()?.Trim();
            Console.Write("Nội dung: ");
            string? body = Console.ReadLine()?.Trim();
            if (string.IsNullOrEmpty(target) || string.IsNullOrEmpty(body)) { Log("Thiếu thông tin.", ConsoleColor.Red); return; }
            try
            {
                using var c = new UdpClient();
                var ep = new IPEndPoint(IPAddress.Parse(_serverIP), _serverPort);
                var payload = Protocol.Build(Protocol.PRV, $"{target}|{body}");
                var data = Encoding.UTF8.GetBytes(payload);
                c.Send(data, data.Length, ep);
                Log("Đã gửi yêu cầu tới server.", ConsoleColor.Green);
            }
            catch (Exception ex) { Log($"Lỗi: {ex.Message}", ConsoleColor.Red); }
        }

        private void UtilitiesMenu()
        {
            while (true)
            {
                Console.ForegroundColor = ConsoleColor.DarkYellow;
                Console.WriteLine("\n--- TIỆN ÍCH (Utilities) ---");
                Console.ResetColor();
                Console.WriteLine(" 1. Xuất lịch sử chat ra .docx");
                Console.WriteLine(" 2. Thay đổi interval PING (ms)");
                Console.WriteLine(" 3. Bật/Tắt Auto-Reconnect");
                Console.WriteLine(" 4. Thay tên (nickname)");
                Console.WriteLine(" 5. Quay lại");
                Console.Write("Chọn: ");
                string? c = Console.ReadLine()?.Trim();
                switch (c)
                {
                    case "1":
                        Console.Write("Tên file (no ext): ");
                        string? fn = Console.ReadLine()?.Trim();
                        if (string.IsNullOrWhiteSpace(fn)) fn = $"client_{DateTime.Now:yyyyMMdd_HHmmss}";
                        UtilExportDocx(fn);
                        break;
                    case "2":
                        Console.Write($"Ping interval (ms) [{_pingInterval}]: ");
                        string? pi = Console.ReadLine()?.Trim();
                        if (int.TryParse(pi, out int v) && v > 0)
                        {
                            _pingInterval = v;
                            Log($"Ping interval set to {v} ms", ConsoleColor.Green);
                        }
                        else Log("Giá trị không hợp lệ.", ConsoleColor.Red);
                        break;
                    case "3":
                        _autoReconnect = !_autoReconnect;
                        Log($"Auto-Reconnect: {(_autoReconnect ? "ON" : "OFF")}", ConsoleColor.Cyan);
                        break;
                    case "4":
                        Console.Write("Nhập tên mới: ");
                        string? nn = Console.ReadLine()?.Trim();
                        if (!string.IsNullOrEmpty(nn))
                        {
                            _nickname = nn;
                            Log($"Nickname đổi thành: {_nickname}", ConsoleColor.Green);
                        }
                        break;
                    case "5": return;
                    default:
                        Log("Lựa chọn không hợp lệ.", ConsoleColor.Red);
                        break;
                }
            }
        }

        // ── Cấu hình ──────────────────────────────────────────
        private void ConfigFlow()
        {
            Console.Write($"Server IP [{_serverIP}]: ");
            string? ip = Console.ReadLine()?.Trim();
            if (!string.IsNullOrEmpty(ip)) _serverIP = ip;

            Console.Write($"Server Port [{_serverPort}]: ");
            string? port = Console.ReadLine()?.Trim();
            if (!string.IsNullOrEmpty(port) && int.TryParse(port, out int p))
                _serverPort = p;

            Log($"Cấu hình: {_serverIP}:{_serverPort}", ConsoleColor.Green);
        }

        // ── Luồng kết nối ─────────────────────────────────────
        private void ConnectFlow()
        {
            // Try to discover server on LAN first
            try
            {
                if (DiscoverServer())
                {
                    Log($"Tìm thấy server: {_serverIP}:{_serverPort}", ConsoleColor.Green);
                }
                else
                {
                    Log("Không tìm thấy server trên LAN. Sử dụng cấu hình hiện tại.", ConsoleColor.DarkYellow);
                }
            }
            catch { }

            // 1) Nhập nickname
            Console.Write("Nhập tên hiển thị: ");
            string? nick = Console.ReadLine()?.Trim();
            if (string.IsNullOrEmpty(nick))
            {
                Log("Tên không được trống.", ConsoleColor.Red);
                return;
            }
            _nickname = nick;
            _nickname = nick;

            // 2) Khởi tạo UDP socket
            try
            {
                _udp = new UdpClient();
                _serverEP = new IPEndPoint(IPAddress.Parse(_serverIP), _serverPort);
                _udp.Connect(_serverEP);          // "kết nối" mặc định (UDP vẫn connectionless)
            }
            catch (Exception ex)
            {
                Log($"Không thể khởi tạo socket: {ex.Message}", ConsoleColor.Red);
                return;
            }

            // 3) Gửi JOIN
            _state = ConnectionState.Connecting;
            _running = true;

            // ── Luồng nhận (ReceiveThread) ─────────────────────
            Thread recvThread = new Thread(ReceiveLoop)
            { IsBackground = true, Name = "ClientReceive" };

            // ── Luồng PING giữ kết nối (PingThread) ───────────
            Thread pingThread = new Thread(PingLoop)
            { IsBackground = true, Name = "ClientPing" };

            recvThread.Start();
            pingThread.Start();

            // Gửi JOIN và chờ phản hồi
            SendRaw(Protocol.Build(Protocol.JOIN, _nickname));

            // Chờ xác nhận kết nối (tối đa 5 giây)
            int waited = 0;
            while (_state == ConnectionState.Connecting && waited < 50)
            {
                Thread.Sleep(100);
                waited++;
            }

            if (_state != ConnectionState.Connected)
            {
                Log("Không nhận được phản hồi từ server. Thử lại sau.", ConsoleColor.Red);
                Disconnect(sendQuit: false);
                return;
            }

            // 4) Giao diện chat
            ChatLoop();

            // 5) Dọn dẹp khi thoát
            recvThread.Join(2000);
            pingThread.Join(2000);
        }

        private bool DiscoverServer(int timeoutMs = 3000)
        {
            try
            {
                using var client = new UdpClient();
                client.EnableBroadcast = true;
                var msg = Encoding.UTF8.GetBytes(Protocol.Build(Protocol.DISCOVER));
                var broadcastEP = new IPEndPoint(IPAddress.Broadcast, _serverPort);
                client.Client.SendTimeout = timeoutMs;
                client.Send(msg, msg.Length, broadcastEP);

                var ar = client.BeginReceive(null, null);
                bool ok = ar.AsyncWaitHandle.WaitOne(timeoutMs);
                if (!ok) return false;

                IPEndPoint remote = new IPEndPoint(IPAddress.Any, 0);
                byte[] data = client.EndReceive(ar, ref remote);
                string raw = Encoding.UTF8.GetString(data);
                var (cmd, body) = Protocol.Parse(raw);
                if (cmd == Protocol.OK)
                {
                    _serverIP = remote.Address.ToString();
                    _serverPort = remote.Port;
                    return true;
                }
            }
            catch { }
            return false;
        }

        // ── Giao diện chat (SendThread ≈ thread chính của chat) ─
        private void ChatLoop()
        {
            PrintChatBanner();

            while (_running && _state == ConnectionState.Connected)
            {
                string? input = Console.ReadLine();
                if (input == null) continue;

                string trimmed = input.Trim();

                if (string.IsNullOrEmpty(trimmed)) continue;

                // Lệnh nội bộ
                if (trimmed.StartsWith('/'))
                {
                    HandleCommand(trimmed);
                }
                else
                {
                    // Gửi tin nhắn bình thường
                    SendRaw(Protocol.Build(Protocol.MSG, trimmed));
                }
            }
        }

        // ── Xử lý lệnh "/" ────────────────────────────────────
        private void HandleCommand(string cmd)
        {
            string lower = cmd.ToLower();
            switch (lower)
            {
                case "/quit":
                case "/exit":
                case "/q":
                    Disconnect(sendQuit: true);
                    break;

                case "/help":
                    PrintChatHelp();
                    break;

                case "/status":
                    Log($"Trạng thái: {_state} | Server: {_serverIP}:{_serverPort} | Tên: {_nickname}",
                        ConsoleColor.Cyan);
                    break;

                case "/clear":
                    Console.Clear();
                    PrintChatBanner();
                    break;

                default:
                    if (lower.StartsWith("/msg "))
                    {
                        // Cho phép gửi tin nhắn thủ công với tiền tố
                        string body = cmd[5..].Trim();
                        if (!string.IsNullOrEmpty(body))
                            SendRaw(Protocol.Build(Protocol.MSG, body));
                    }
                    else
                    {
                        Log($"Lệnh không rõ: {cmd}. Gõ /help để xem hướng dẫn.", ConsoleColor.DarkGray);
                    }
                    break;
            }
        }

        // ── Vòng lặp nhận (chạy trong ReceiveThread) ──────────
        private void ReceiveLoop()
        {
            while (_running)
            {
                try
                {
                    IPEndPoint any = new IPEndPoint(IPAddress.Any, 0);
                    byte[] data = _udp!.Receive(ref any);
                    string raw = Encoding.UTF8.GetString(data);
                    HandleServerMessage(raw);
                }
                catch (SocketException) when (!_running) { break; }
                catch (ObjectDisposedException) { break; }
                catch (Exception ex)
                {
                    if (_running)
                        Log($"[Receive] Lỗi: {ex.Message}", ConsoleColor.Red);
                }
            }
        }

        // ── Xử lý phản hồi từ server ──────────────────────────
        private void HandleServerMessage(string raw)
        {
            var (cmd, body) = Protocol.Parse(raw);

            switch (cmd)
            {
                case Protocol.OK:
                    if (_state == ConnectionState.Connecting)
                    {
                        _state = ConnectionState.Connected;
                        Log($"[Server] {body}", ConsoleColor.Green);
                    }
                    else
                    {
                        // Xác nhận tin nhắn — có thể im lặng hoặc hiện nhỏ
                        // Log($"[ACK] {body}", ConsoleColor.DarkGray);
                    }
                    break;

                case Protocol.ERR:
                    Log($"[Lỗi Server] {body}", ConsoleColor.Red);
                    if (_state == ConnectionState.Connecting)
                    {
                        _running = false;
                        _state = ConnectionState.Disconnected;
                    }
                    break;

                case Protocol.BROADCAST:
                    // Tin nhắn từ client khác hoặc admin
                    PrintMessage(body);
                    break;

                case Protocol.SYS:
                    // Thông báo hệ thống (ai vào/rời)
                    lock (_consoleLock)
                    {
                        Console.ForegroundColor = ConsoleColor.Yellow;
                        Console.WriteLine($"  *** {body}");
                        Console.ResetColor();
                    }
                    break;

                default:
                    Log($"[Server] {raw}", ConsoleColor.DarkGray);
                    break;
            }
        }

        // ── Vòng lặp PING (PingThread) ────────────────────────
        private void PingLoop()
        {
            while (_running)
            {
                Thread.Sleep(_pingInterval);
                if (_state == ConnectionState.Connected)
                    SendRaw(Protocol.PING);
            }
        }

        // ── Gửi dữ liệu thô ───────────────────────────────────
        private void SendRaw(string message)
        {
            try
            {
                byte[] data = Encoding.UTF8.GetBytes(message);
                _udp!.Send(data, data.Length);
            }
            catch (Exception ex)
            {
                Log($"[Send] Lỗi: {ex.Message}", ConsoleColor.Red);
            }
        }

        // ── Ngắt kết nối ──────────────────────────────────────
        private void Disconnect(bool sendQuit)
        {
            _running = false;
            if (sendQuit && _state == ConnectionState.Connected)
            {
                SendRaw(Protocol.QUIT);
                Thread.Sleep(300); // cho server xử lý
            }
            _state = ConnectionState.Disconnected;
            _udp?.Close();
            Log("Đã ngắt kết nối.", ConsoleColor.Yellow);
        }

        // ── In tin nhắn chat ───────────────────────────────────
        private void PrintMessage(string line)
        {
            lock (_consoleLock)
            {
                // Tô màu khác nhau nếu là tin nhắn của mình
                bool isMine = line.StartsWith($"[{_nickname}]:");
                Console.ForegroundColor = isMine ? ConsoleColor.Cyan : ConsoleColor.White;
                Console.WriteLine($"\r  {line}");
                try
                {
                    _history.Enqueue(line);
                    while (_history.Count > 1000) _history.TryDequeue(out _);
                }
                catch { }
                Console.ResetColor();
            }
        }

        // ── Tiện ích hiển thị ──────────────────────────────────
        private void Log(string msg, ConsoleColor color = ConsoleColor.Gray)
        {
            lock (_consoleLock)
            {
                string timestamp = DateTime.Now.ToString("HH:mm:ss");
                string full = $"[{timestamp}] {msg}";
                try
                {
                    _history.Enqueue(full);
                    while (_history.Count > 1000) _history.TryDequeue(out _);
                }
                catch { }

                Console.ForegroundColor = ConsoleColor.DarkGray;
                Console.Write($"[{timestamp}] ");
                Console.ForegroundColor = color;
                string icon = color switch
                {
                    ConsoleColor.Green => "✔",
                    ConsoleColor.Yellow => "⚠",
                    ConsoleColor.Red => "✖",
                    ConsoleColor.Cyan => "◆",
                    ConsoleColor.Magenta => "✦",
                    _ => "•"
                };
                Console.WriteLine($"{icon} {msg}");
                Console.ResetColor();
            }
        }

        private static string CenterText(string text, int width)
        {
            if (text.Length >= width) return text[..width];
            int left = (width - text.Length) / 2;
            return new string(' ', left) + text + new string(' ', width - text.Length - left);
        }

        private void UtilExportDocx(string filename)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(filename))
                    filename = $"client_{DateTime.Now:yyyyMMdd_HHmmss}";
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

                Log($"Đã xuất lịch sử ra: {filename}", ConsoleColor.Green);
            }
            catch (Exception ex)
            {
                Log($"Lỗi khi xuất DOCX: {ex.Message}", ConsoleColor.Red);
            }
        }

        private void PrintBanner()
        {
            Console.ForegroundColor = ConsoleColor.Cyan;
            Console.WriteLine(@"
╔══════════════════════════════════════════════════╗
║          UDP CHAT CLIENT  –  C#  .NET 8          ║
║  Giao thức : UDP / Đa luồng                      ║
╚══════════════════════════════════════════════════╝");
            Console.ResetColor();
        }

        private void PrintChatBanner()
        {
            Console.ForegroundColor = ConsoleColor.DarkGreen;
            Console.WriteLine();
            Console.WriteLine("╔════════════════════════════════════════════════════════╗");
            Console.WriteLine($"║ {CenterText($" Chat — {_nickname} @ {_serverIP}:{_serverPort}", 54)} ║");
            Console.WriteLine("╠════════════════════════════════════════════════════════╣");
            Console.WriteLine("║  Nhập tin nhắn và nhấn Enter để gửi. Gõ /help để xem lệnh. ║");
            Console.WriteLine("╚════════════════════════════════════════════════════════╝\n");
            Console.ResetColor();
        }

        private void PrintChatHelp()
        {
            lock (_consoleLock)
            {
                Console.ForegroundColor = ConsoleColor.DarkGray;
                Console.WriteLine("\n╔────── Commands ─────────────────────────────╗");
                Console.WriteLine("║ /quit | /q    – Thoát và ngắt kết nối       ║");
                Console.WriteLine("║ /status       – Xem trạng thái kết nối       ║");
                Console.WriteLine("║ /clear        – Xóa màn hình                 ║");
                Console.WriteLine("║ /help         – Hiển thị trợ giúp này         ║");
                Console.WriteLine("║ <text>        – Gửi tin nhắn                 ║");
                Console.WriteLine("╚──────────────────────────────────────────────╝\n");
                Console.ResetColor();
            }
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
                new Client().Start();
            }
            catch (Exception ex)
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine($"Lỗi client: {ex.Message}");
                Console.ResetColor();
            }
        }
    }
}