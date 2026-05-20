using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Windows.Forms;

namespace AdminGUI
{
    public partial class Form1 : Form
    {
        public Form1()
        {
            InitializeComponent();
        }

        private void btnRefresh_Click(object sender, EventArgs e)
        {
            RefreshPending();
        }

        private void RefreshPending()
        {
            lstPending.Items.Clear();
            try
            {
                using var udp = new UdpClient();
                udp.Client.ReceiveTimeout = 2000;
                var server = new IPEndPoint(IPAddress.Parse(txtServerIP.Text.Trim()), int.Parse(txtServerPort.Text.Trim()));
                var payload = Encoding.UTF8.GetBytes("ADMIN:LISTPENDING");
                udp.Send(payload, payload.Length, server);
                var remote = new IPEndPoint(IPAddress.Any, 0);
                var resp = udp.Receive(ref remote);
                var text = Encoding.UTF8.GetString(resp);
                if (text.StartsWith("OK:"))
                {
                    var body = text.Substring(3);
                    if (string.IsNullOrEmpty(body)) return;
                    var parts = body.Split(',', StringSplitOptions.RemoveEmptyEntries);
                    foreach (var p in parts)
                    {
                        // format key=name
                        lstPending.Items.Add(p.Trim());
                    }
                }
                else
                {
                    MessageBox.Show("Phản hồi lỗi: " + text, "Lỗi", MessageBoxButtons.OK, MessageBoxIcon.Error);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("Không thể kết nối server: " + ex.Message, "Lỗi", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void btnAccept_Click(object sender, EventArgs e)
        {
            if (lstPending.SelectedItem == null) return;
            var item = lstPending.SelectedItem.ToString();
            var key = item?.Split('=')[0]?.Trim();
            if (string.IsNullOrEmpty(key)) return;
            SendAdminCommand($"ACCEPT:{key}");
            RefreshPending();
        }

        private void btnReject_Click(object sender, EventArgs e)
        {
            if (lstPending.SelectedItem == null) return;
            var item = lstPending.SelectedItem.ToString();
            var key = item?.Split('=')[0]?.Trim();
            if (string.IsNullOrEmpty(key)) return;
            SendAdminCommand($"REJECT:{key}");
            RefreshPending();
        }

        private void SendAdminCommand(string cmd)
        {
            try
            {
                using var udp = new UdpClient();
                udp.Client.ReceiveTimeout = 2000;
                var server = new IPEndPoint(IPAddress.Parse(txtServerIP.Text.Trim()), int.Parse(txtServerPort.Text.Trim()));
                var payload = Encoding.UTF8.GetBytes("ADMIN:" + cmd);
                udp.Send(payload, payload.Length, server);
                var remote = new IPEndPoint(IPAddress.Any, 0);
                var resp = udp.Receive(ref remote);
                var text = Encoding.UTF8.GetString(resp);
                MessageBox.Show("Phản hồi: " + text, "Kết quả", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Gửi lệnh thất bại: " + ex.Message, "Lỗi", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
