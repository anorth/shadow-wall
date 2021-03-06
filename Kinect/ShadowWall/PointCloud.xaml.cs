﻿using Microsoft.Kinect;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Media.Media3D;
using System.Windows.Threading;

namespace ShadowWall
{
	/// <summary>
	/// Interaction logic for MainWindow.xaml
	/// </summary>
	public partial class PointCloud : Window, INotifyPropertyChanged
	{
		public PointCloud()
		{
			InitializeComponent();

			this.Loaded += PointCloud_Loaded;
			this.Closed += PointCloud_Closed;
			this.KeyDown += PointCloud_KeyDown;
			this.MouseWheel += PointCloud_MouseWheel;

			var sensor = KinectSensor.GetDefault();
			sensor.Open();

			var depthReader = sensor.DepthFrameSource.OpenReader();
			depthReader.FrameArrived += depthReader_FrameArrived;

			var bodyReader = sensor.BodyFrameSource.OpenReader();
			CurrentCloud = new List<PointFrame>();

			filters = new IPointCloudFilter[]
			{
				new AgingFilter()
			};

			DataContext = this;
		}

		void PointCloud_Closed(object sender, EventArgs e)
		{
			KinectSensor.GetDefault().Close();
		}

		void depthReader_FrameArrived(object sender, DepthFrameArrivedEventArgs e)
		{
			using (var frame = e.FrameReference.AcquireFrame())
			{
				if (frame != null)
				{
					var width = frame.FrameDescription.Width;
					var height = frame.FrameDescription.Height;
					var depths = new ushort[width * height];

					frame.CopyFrameDataToArray(depths);

					if (IsRecording)
					{
						RecordDepths(depths);
					}

					for (int i = 0; i < depths.Length; ++i)
					{
						depths[i] = depths[i] > (this.WallBreadth * 10) ? default(ushort) : depths[i];
					}

					Clear(Mesh);
					var newCloud = ConvertToPointCloud(depths, width, height);

					foreach (var filter in filters)
					{
						filter.Apply(newCloud);
					}

					//DrawTriangleCloud(newCloud);
					DrawDepthCloud(newCloud, width, height);

					lock (currentCloudLock)
					{
						CurrentCloud = newCloud;
					}
					Flush();
				}
			}
		}

		void RecordDepths(ushort[] depths)
		{
			var recordString = string.Join(",", depths) + Environment.NewLine;
			var byteCount = Encoding.UTF8.GetByteCount(recordString);
			RecordFileStream.Write(Encoding.UTF8.GetBytes(recordString), 0, byteCount);
		}

		IEnumerable<PointFrame> ConvertToPointCloud(ushort[] depths, int width, int height)
		{
			var points = new List<PointFrame>();

			for (int i = 0; i < depths.Length; ++i)
			{
				var item = depths[i];
				var x = (i % width) * this.WallWidth / (float)width;
				var y = (height - i / width) * this.WallHeight / (float)height;
				var z = item > 0 ? this.WallBreadth - (((float)item / (this.WallBreadth * 10)) * this.WallBreadth) : 0;

				var b = item / 3;
				var g = (item - b) / 3;
				var r = (item - b - g) / 3;

				points.Add(new PointFrame() { X = x, Y = y, Z = z, R = (byte)r, G = (byte)g, B = (byte)b });
			}

			return points;
		}

		void DrawTriangleCloud(IEnumerable<PointFrame> cloud)
		{
			foreach (var point in cloud)
			{
				if (point.Z > 0)
				{
					DrawPoint(Mesh, (int)point.X, (int)point.Y, (int)point.Z, (byte)point.R, (byte)point.G, (byte)point.B);
				}
			}
		}

		void DrawDepthCloud(IEnumerable<PointFrame> cloud, int width, int height)
		{
			var byteCloud = ConvertToByteArray(cloud);
			DepthImage.Source = BitmapSource.Create(width, height, 96, 96, PixelFormats.Bgr32, BitmapPalettes.WebPalette, byteCloud, width * PixelFormats.Bgr32.BitsPerPixel / 8);
		}

		private byte[] ConvertToByteArray(IEnumerable<PointFrame> cloud)
		{
			var bytes = new byte[cloud.Count() * (PixelFormats.Bgr32.BitsPerPixel / 8)];

			var index = 0;
			foreach (var point in cloud)
			{
				bytes[index++] = (byte)point.B; // Blue
				bytes[index++] = (byte)point.G; // Green
				bytes[index++] = (byte)point.B; // Red
				bytes[index++] = 0; // Alpha
			}

			return bytes;
		}

		void snapshotButton_Click(object sender, EventArgs e)
		{
			IEnumerable<PointFrame> cloudToSave;
			lock (currentCloudLock)
			{
				cloudToSave = CurrentCloud.ToArray();
			}
			Task.Factory.StartNew(() =>
			{
				var serializer = new Serializer(snapshotsTaken++.ToString());
				foreach (var point in cloudToSave)
				{
					serializer.Save((int)point.X, (int)point.Y, (int)point.Z, (byte)point.R, (byte)point.G, (byte)point.B);
				}
			});
		}

		void recordButton_Click(object sender, EventArgs e)
		{
			if (!IsRecording)
			{
				var recordFile = Path.Combine(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location), string.Format("ShadowWallRecording{0}.csv", recordingsMade++));
				RecordFileStream = new FileStream(recordFile, FileMode.Create, FileAccess.Write);
			}
			else
			{
				RecordFileStream.Flush();
				RecordFileStream.Dispose();
			}

			IsRecording = !IsRecording;
		}

		#region 3D

		void PointCloud_Loaded(object sender, RoutedEventArgs e)
		{
		}

		void PointCloud_KeyDown(object sender, KeyEventArgs e)
		{
			switch (e.Key)
			{
				case Key.Up:
					RotateX.Angle += 10;
					break;
				case Key.Down:
					RotateX.Angle -= 10;
					break;
				case Key.Left:
					RotateY.Angle -= 10;
					break;
				case Key.Right:
					RotateY.Angle += 10;
					break;
				case Key.W:
					Camera.Position = new Point3D(Camera.Position.X, Camera.Position.Y - 50, Camera.Position.Z);
					break;
				case Key.S:
					Camera.Position = new Point3D(Camera.Position.X, Camera.Position.Y + 50, Camera.Position.Z);
					break;
				case Key.A:
					Camera.Position = new Point3D(Camera.Position.X + 50, Camera.Position.Y, Camera.Position.Z);
					break;
				case Key.D:
					Camera.Position = new Point3D(Camera.Position.X - 50, Camera.Position.Y, Camera.Position.Z);
					break;
				default:
					break;
			}
		}

		void PointCloud_MouseWheel(object sender, MouseWheelEventArgs e)
		{
			if (e.Delta > 0)
			{
				Camera.Position = new Point3D(Camera.Position.X + 50, Camera.Position.Y - 50, Camera.Position.Z - 50);
			}
			else
			{
				Camera.Position = new Point3D(Camera.Position.X - 50, Camera.Position.Y + 50, Camera.Position.Z + 50);
			}
		}

		void DrawPoint(MeshGeometry3D mesh, int x, int y, int z, byte r, byte g, byte b)
		{
			var count = mesh.Positions.Count;
			var color = new Color() { A = 0, R = r, G = g, B = b };

			mesh.Positions.Add(new Point3D(x - 0.5, y - 0.5, z + 0.5));
			mesh.Positions.Add(new Point3D(x + 0.5, y + 0.5, z + 0.5));
			mesh.Positions.Add(new Point3D(x - 0.5, y + 0.5, z + 0.5));

			mesh.TriangleIndices.Add(0 + count);
			mesh.TriangleIndices.Add(1 + count);
			mesh.TriangleIndices.Add(2 + count);
		}

		void Clear(MeshGeometry3D mesh)
		{
			mesh.Positions.Clear();
			mesh.TriangleIndices.Clear();
		}

		void Flush()
		{
			Dispatcher.CurrentDispatcher.Invoke(DispatcherPriority.Background, new ThreadStart(delegate { }));
		}

		#endregion

		public event PropertyChangedEventHandler PropertyChanged;
		public int WallWidth { get { return 180; } }
		public int WallHeight { get { return 120; } }
		public int WallBreadth { get { return 800; } }
		public IEnumerable<PointFrame> CurrentCloud { get; private set; }
		public string RecordButtonContent
		{
			get
			{
				return IsRecording ? "Stop recording" : "Start recording";
			}
		}

		bool IsRecording
		{
			get
			{
				return isRecording;
			}
			set
			{
				isRecording = value;
				PropertyChanged(this, new PropertyChangedEventArgs("RecordButtonContent"));
			}
		}

		#region Recording state

		bool isRecording = false;
		Stream RecordFileStream { get; set; }
		int recordingsMade = 0;

		#endregion

		#region Snapshot state

		object currentCloudLock = new object();
		int snapshotsTaken = 0;

		#endregion

		IEnumerable<IPointCloudFilter> filters;
	}
}
