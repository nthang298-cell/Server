using System;
using System.Collections.Concurrent;
using System.Drawing;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;

namespace ClientGUI
{
    public partial class Form1 : Form
    {
        private UdpClient? _udp;
        private IPEndPoint? _serverEP;
        private readonly ConcurrentQueue<string> _history = new();

        public Form1()
        {
            InitializeComponent();
        }

        private void btnConnect_Click(object sender, EventArgs e)
        {
            try
            {
                _udp = new UdpClient();
                _serverEP = new IPEndPoint(IPAddress.Parse(txtServerIP.Text), int.Parse(txtServerPort.Text));
                _udp.Connect(_serverEP);
                AppendLog("Connected to server", Color.Green);
                ThreadPool.QueueUserWorkItem(_ => ReceiveLoop());
            }
            catch (Exception ex)
            {
                AppendLog("Error: " + ex.Message, Color.Red);
            }
        }

        private void ReceiveLoop()
        {
            try
            {
                while (true)
                {
                    IPEndPoint any = new IPEndPoint(IPAddress.Any, 0);
                    byte[] data = _udp!.Receive(ref any);
                    string raw = Encoding.UTF8.GetString(data);
                    this.BeginInvoke(() => AppendLog(raw, Color.Black));
                }
            }
            catch { }
        }

        private void btnSend_Click(object sender, EventArgs e)
        {
            try
            {
                var txt = txtMessage.Text;
                byte[] data = Encoding.UTF8.GetBytes(txt);
                _udp!.Send(data, data.Length);
                AppendLog("Me: " + txt, Color.Blue);
            }
            catch (Exception ex)
            {
                AppendLog("Send error: " + ex.Message, Color.Red);
            }
        }

        private void AppendLog(string text, Color color)
        {
            if (string.IsNullOrEmpty(text)) return;
            _history.Enqueue(text);
            if (_history.Count > 2000) _history.TryDequeue(out _);

            txtLog.SelectionStart = txtLog.TextLength;
            txtLog.SelectionLength = 0;
            txtLog.SelectionColor = color;
            txtLog.AppendText(text + Environment.NewLine);
            txtLog.SelectionColor = txtLog.ForeColor;
        }

        private void btnExport_Click(object sender, EventArgs e)
        {
            try
            {
                string filename = "chat_gui_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".docx";
                using var mem = new System.IO.MemoryStream();
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
                System.IO.File.WriteAllBytes(filename, mem.ToArray());
                AppendLog("Exported: " + filename, Color.Green);
            }
            catch (Exception ex)
            {
                AppendLog("Export error: " + ex.Message, Color.Red);
            }
        }
    }
}
