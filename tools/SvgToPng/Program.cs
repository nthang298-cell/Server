using System;
using System.IO;
using SkiaSharp;
using Svg.Skia;

var input = args.Length > 0 ? args[0] : "docs/diagrams/insert_node.svg";
var output = args.Length > 1 ? args[1] : "docs/diagrams/insert_node.png";

using var svg = new SKSvg();
svg.Load(input);
var picture = svg.Picture;
if (picture == null) Environment.Exit(2);
var width = (int)picture.CullRect.Width;
var height = (int)picture.CullRect.Height;
using var bitmap = new SKBitmap(width, height);
using var canvas = new SKCanvas(bitmap);
canvas.Clear(SKColors.White);
canvas.DrawPicture(picture);
canvas.Flush();
using var image = SKImage.FromBitmap(bitmap);
using var data = image.Encode(SKEncodedImageFormat.Png, 100);
using var fs = File.OpenWrite(output);
data.SaveTo(fs);
Console.WriteLine($"Wrote {output}");
